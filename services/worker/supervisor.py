import hashlib
import json
import os
import smtplib
import subprocess
import sys
import tempfile
import time
from email.message import EmailMessage
from pathlib import Path

import psutil
from filelock import FileLock, Timeout

from services.api import config
from services.api.db import canonical, migrate, transaction, uid
from services.api.domain import Candidate, event_key, validate_evidence


def kill_tree(pid):
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            child.terminate()
        parent.terminate()
        _, alive = psutil.wait_procs([parent, *children], timeout=5)
        for p in alive:
            p.kill()
    except psutil.NoSuchProcess:
        pass


def run_stage(job, stage, spec):
    folder = config.DATA / 'jobs' / job['id']
    folder.mkdir(parents=True, exist_ok=True)
    spec['run_dir'] = str(folder)
    source = folder / f'{stage}-input.json'
    target = folder / f'{stage}-output.json'
    source.write_text(canonical(spec), encoding='utf-8')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    receipt = folder / f'{stage}-receipt.json'
    if target.exists() and receipt.exists() and json.loads(receipt.read_text())['input_hash'] == digest:
        return json.loads(target.read_text(encoding='utf-8'))
    with transaction() as c:
        c.execute("UPDATE jobs SET stage=?,lease=? WHERE id=?", (stage, time.time() + 30, job['id']))
        c.execute("UPDATE meetings SET status=? WHERE id=?", ('transcribing' if stage == 'whisper' else 'reconciling', job['meeting_id']))
    log = open(folder / f'{stage}.log', 'wb')
    env = {**os.environ, 'HF_HUB_OFFLINE': '1', 'CUDA_VISIBLE_DEVICES': '0'}
    proc = subprocess.Popen([sys.executable, '-m', 'services.worker.stage', stage, str(source), str(target)],
                            stdout=log, stderr=log, cwd=config.ROOT, env=env)
    started, peak_ram = time.time(), 0
    try:
        while proc.poll() is None:
            with transaction() as c:
                row = c.execute("SELECT cancel FROM jobs WHERE id=?", (job['id'],)).fetchone()
                c.execute("UPDATE jobs SET lease=? WHERE id=?", (time.time() + 30, job['id']))
            if row['cancel']:
                raise RuntimeError('cancelled')
            if time.time() - started > 7200:
                raise RuntimeError('stage_timeout')
            try:
                parent = psutil.Process(proc.pid)
                peak_ram = max(peak_ram, sum(p.memory_info().rss for p in [parent, *parent.children(recursive=True)]))
            except psutil.Error:
                pass
            time.sleep(.5)
        if proc.returncode != 0:
            raise RuntimeError(stage + '_failed_see_local_log')
        output = json.loads(target.read_text(encoding='utf-8'))
        receipt.write_text(canonical({'input_hash': digest, 'output_hash': hashlib.sha256(target.read_bytes()).hexdigest(),
                                      'elapsed_seconds': time.time()-started, 'peak_process_ram_bytes': peak_ram,
                                      'peak_vram': None, 'contract_version': 1}), encoding='utf-8')
        return output
    finally:
        if proc.poll() is None:
            kill_tree(proc.pid)
        proc.wait()
        log.close()


def process(job):
    with transaction() as c:
        asset = dict(c.execute('SELECT * FROM assets WHERE id=?', (job['asset_id'],)).fetchone())
        meeting = dict(c.execute('SELECT * FROM meetings WHERE id=?', (job['meeting_id'],)).fetchone())
    spec = {'audio': asset['path'], 'config': json.loads(job['config']), 'meeting': meeting}
    asr = run_stage(job, 'whisper', spec)
    with transaction() as c:
        existing = c.execute('SELECT * FROM segments WHERE asset_id=? ORDER BY start', (asset['id'],)).fetchall()
        if not existing:
            for s in asr['segments']:
                c.execute('INSERT INTO segments(id,meeting_id,asset_id,revision,start,end,text,raw,words) VALUES(?,?,?,1,?,?,?,?,?)',
                          (uid(), meeting['id'], asset['id'], s['start'], s['end'], s['text'], canonical(s['raw']), canonical(s['words'])))
        segments = [dict(r) for r in c.execute('SELECT * FROM segments WHERE asset_id=? ORDER BY start', (asset['id'],))]
    spec['segments'] = [{k: s[k] for k in ('id', 'revision', 'start', 'end', 'text')} for s in segments]
    extracted = run_stage(job, 'extract', spec) if segments else {'events': []}
    source = {s['id']: s for s in segments}
    validated = []
    for e in extracted['events']:
        event = Candidate.model_validate(e)
        validated.append((event, validate_evidence(event, source)))
    with transaction() as c:
        for event, evidence in validated:
            body = event.model_dump()
            ident = event_key(body)
            # Scope semantic key to meeting; same utterance in another meeting is distinct.
            ident = hashlib.sha256((meeting['id'] + ident).encode()).hexdigest()
            if c.execute('SELECT 1 FROM candidates WHERE id=?', (ident,)).fetchone():
                continue
            position = min(source[e['segment_id']]['start'] for e in evidence)
            c.execute('INSERT INTO candidates(id,meeting_id,subject,body,source_order,created) VALUES(?,?,?,?,?,?)',
                      (ident, meeting['id'], event.subject, canonical(body), position, time.time()))
            for e in evidence:
                c.execute('INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?)', (uid(), meeting['id'], ident,
                          e['segment_id'], e['revision'], e['field'], e['quote'], e['start'], e['end']))
        c.execute("UPDATE jobs SET state='complete',stage='awaiting_review',lease=0 WHERE id=?", (job['id'],))
        c.execute("UPDATE meetings SET status='awaiting_review',revision=revision+1 WHERE id=?", (meeting['id'],))


def deliver_one():
    with transaction() as c:
        c.execute("UPDATE outbox SET state='uncertain',error='worker_interrupted_during_send' WHERE state='sending'")
        row = c.execute("SELECT o.*,s.html,s.body FROM outbox o JOIN snapshots s ON s.id=o.snapshot_id WHERE o.state='queued' ORDER BY o.created LIMIT 1").fetchone()
        if not row:
            return False
        row = dict(row)
        c.execute("UPDATE outbox SET state='sending',attempt=attempt+1 WHERE id=?", (row['id'],))
    msg = EmailMessage()
    msg['From'] = 'minutes@secure-mom.test'
    msg['To'] = ', '.join(json.loads(row['addresses']))
    msg['Subject'] = 'Approved minutes: ' + json.loads(row['body'])['meeting']['title']
    msg['Message-ID'] = row['message_id']
    msg.set_content('Approved meeting minutes are included as HTML. No audio attached.')
    msg.add_alternative(row['html'], subtype='html')
    state, error = 'smtp_accepted', None
    entered_data = False
    try:
        host = os.environ.get('MOM_SMTP_HOST', '127.0.0.1')
        port = int(os.environ.get('MOM_SMTP_PORT', '1025'))
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            entered_data = True
            refused = smtp.send_message(msg)
            if refused:
                state, error = 'uncertain', 'some_recipients_refused'
    except Exception:
        state, error = ('uncertain' if entered_data else 'failed'), 'smtp_transport_error'
    with transaction() as c:
        c.execute('UPDATE outbox SET state=?,error=? WHERE id=?', (state, error, row['id']))
    return True


def tick():
    deliver_one()
    with transaction() as c:
        c.execute("UPDATE jobs SET state='queued',error='lease_recovered' WHERE state='running' AND lease<?", (time.time(),))
        c.execute("UPDATE jobs SET state='cancelled' WHERE state='queued' AND cancel=1")
        row = c.execute("SELECT * FROM jobs WHERE state='queued' AND cancel=0 ORDER BY created LIMIT 1").fetchone()
        if not row:
            return False
        job = dict(row)
        c.execute("UPDATE jobs SET state='running',lease=?,attempt=attempt+1 WHERE id=?", (time.time()+30, job['id']))
    try:
        process(job)
    except Exception as exc:
        code = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        with transaction() as c:
            state = 'cancelled' if code == 'cancelled' else 'failed'
            c.execute('UPDATE jobs SET state=?,error=?,lease=0 WHERE id=?', (state, code[:160], job['id']))
            c.execute("UPDATE meetings SET status='failed' WHERE id=?", (job['meeting_id'],))
    return True


def main():
    migrate()
    # Shared across app data directories so a second installation cannot double-admit models.
    lock = FileLock(str(Path(tempfile.gettempdir()) / 'secure-mom-gpu.lock'), timeout=0)
    try:
        with lock:
            while True:
                tick()
                time.sleep(1)
    except Timeout:
        raise SystemExit('Another Secure MOM supervisor owns GPU admission.')


if __name__ == '__main__':
    main()

