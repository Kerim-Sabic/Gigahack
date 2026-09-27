"""Opt-in local meeting copies. The database and original audio remain authoritative."""
import hashlib
import json
import os
from pathlib import Path
import re
import time
import tempfile

from filelock import FileLock, Timeout

from . import config
from .db import canonical, transaction
from .storage import require_space


def atomic_write(path, content):
    # Unique exclusive temporary files avoid following pre-existing partial-file links.
    fd, name = tempfile.mkstemp(prefix='.notavra-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def export_root():
    configured = os.environ.get('MOM_TRANSCRIPT_EXPORT_DIR')
    return Path(configured) if configured else (Path('C:/notavra/transcriptions') if os.name == 'nt' else config.DATA / 'transcriptions')


def safe_name(title):
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '-', title).strip(' .')[:80].strip(' .')
    if not clean or clean.upper().split('.')[0] in {'CON', 'PRN', 'AUX', 'NUL', *[f'COM{i}' for i in range(1, 10)], *[f'LPT{i}' for i in range(1, 10)]}:
        clean = 'Meeting'
    return clean


def enable(c, meeting):
    root = export_root().resolve()
    folder = root / (safe_name(meeting['title']) + '--' + meeting['id'][:8])
    c.execute('INSERT OR IGNORE INTO meeting_file_exports(meeting_id,folder) VALUES(?,?)',
              (meeting['id'], str(folder)))
    c.execute("UPDATE meeting_file_exports SET state='pending',fingerprint=NULL,error=NULL WHERE meeting_id=?", (meeting['id'],))


def status(c, ident):
    row = c.execute('SELECT folder,state,error,updated FROM meeting_file_exports WHERE meeting_id=?', (ident,)).fetchone()
    return dict(row) if row else {'folder': None, 'state': 'disabled', 'error': None, 'updated': None}


def stamp(samples, rate=16000):
    seconds = samples // rate
    return f'{seconds // 60}:{seconds % 60:02d}'


def snapshot(ident):
    with transaction() as c:
        row = c.execute('SELECT * FROM meetings WHERE id=?', (ident,)).fetchone()
        export = c.execute('SELECT * FROM meeting_file_exports WHERE meeting_id=?', (ident,)).fetchone()
        if not row or not export:
            return None
        assets = [dict(a) for a in c.execute('SELECT * FROM assets WHERE meeting_id=? ORDER BY rowid', (ident,))]
        segments = [dict(s) for s in c.execute('SELECT id,asset_id,start,end,speaker,text,revision,raw FROM segments WHERE meeting_id=? ORDER BY start,rowid', (ident,))]
        jobs = [dict(j) for j in c.execute('SELECT id,state,stage,asset_id FROM jobs WHERE meeting_id=? ORDER BY created', (ident,))]
        return {'meeting': dict(row), 'export': dict(export), 'assets': assets, 'segments': segments, 'jobs': jobs}


def sync_one(ident):
    # One publisher per meeting, including multiple API workers.
    with FileLock(str(config.DATA / f'files-{ident}.lock'), timeout=0):
        data = snapshot(ident)
        if not data:
            return
        meeting, export = data['meeting'], data['export']
        fingerprint = hashlib.sha256(canonical({k: v for k, v in data.items() if k != 'export'}).encode()).hexdigest()
        if export['fingerprint'] == fingerprint and export['state'] == 'ready':
            return
        root = export_root().resolve()
        folder = Path(export['folder'])
        if folder.parent.resolve() != root or folder.is_symlink() or folder.resolve().parent != root:
            raise ValueError('export_folder_boundary')
        folder.mkdir(parents=True, exist_ok=True)
        owner = folder / '.notavra-meeting.json'
        if owner.is_symlink():
            raise ValueError('export_folder_boundary')
        if owner.exists():
            if json.loads(owner.read_text(encoding='utf-8')).get('meeting_id') != ident:
                raise ValueError('export_folder_owner_mismatch')
        elif any(folder.iterdir()):
            raise ValueError('export_folder_not_empty')
        else:
            atomic_write(owner, canonical({'meeting_id': ident}).encode())

        def write(name, content):
            target = folder / name
            if target.is_symlink() or target.resolve().parent != folder.resolve():
                raise ValueError('export_file_boundary')
            require_space(folder, len(content.encode('utf-8')))
            atomic_write(target, content.encode('utf-8'))

        recordings, lines = [], [meeting['title'], f"Meeting date: {meeting['date'] or 'Unknown'}", '',
                                 'Working transcript. Not an approved meeting record.', '']
        for index, asset in enumerate(data['assets'], 1):
            metadata = json.loads(asset['original'])
            normalized = Path(asset['path']).resolve()
            audio_root = (config.DATA / 'audio' / ident).resolve()
            if not normalized.is_relative_to(audio_root):
                raise ValueError('source_audio_boundary')
            source = normalized.parent / metadata.get('file', normalized.name)
            if source.resolve().parent != normalized.parent or source.is_symlink():
                raise ValueError('source_audio_boundary')
            if not source.is_file():
                source = normalized
            extension = source.suffix.lower()
            if extension not in {'.wav', '.mp3', '.m4a', '.ogg', '.flac', '.webm'}:
                extension = '.wav'
            name = f'audio-{index:02d}{extension}'
            destination = folder / name
            if destination.is_symlink() or destination.resolve().parent != folder.resolve():
                raise ValueError('export_file_boundary')
            receipt = folder / (name + '.sha256')
            if receipt.is_symlink():
                raise ValueError('export_file_boundary')
            # Audio is immutable. The receipt avoids recopying a large recording on every text edit.
            if not (destination.is_file() and destination.stat().st_size == source.stat().st_size
                    and receipt.is_file() and receipt.read_text() == asset['hash']):
                require_space(folder, source.stat().st_size)
                temporary = folder / (name + '.partial')
                if temporary.is_symlink():
                    raise ValueError('export_file_boundary')
                digest = hashlib.sha256()
                with source.open('rb') as incoming, temporary.open('wb') as outgoing:
                    while chunk := incoming.read(1024 * 1024):
                        outgoing.write(chunk)
                        digest.update(chunk)
                    outgoing.flush()
                    os.fsync(outgoing.fileno())
                if digest.hexdigest() != asset['hash']:
                    temporary.unlink(missing_ok=True)
                    raise ValueError('source_audio_hash_mismatch')
                os.replace(temporary, destination)
                write(name + '.sha256', asset['hash'])
            segments = [s for s in data['segments'] if s['asset_id'] == asset['id']]
            recordings.append({'file': name, 'name': metadata.get('filename', f'Recording {index}'),
                               'asset_id': asset['id'], 'duration_seconds': asset['samples'] / asset['sample_rate'],
                               'transcript_status': 'available' if segments else 'not_available', 'segments': segments})
            lines.extend([f'Audio: {name}', ''])
            if not segments:
                lines.extend(['[Transcript not available for this recording yet.]', ''])
            for segment in segments:
                lines.extend([segment['speaker'] or 'Speaker unknown', stamp(segment['start']), segment['text'], ''])
        if data['segments']:
            write('transcript.txt', '\n'.join(lines))
            template = folder / 'transcript-template.txt'
            if not template.is_symlink():
                template.unlink(missing_ok=True)
        else:
            # A template is never presented as an actual transcript.
            previous_text = folder / 'transcript.txt'
            if not previous_text.is_symlink():
                previous_text.unlink(missing_ok=True)
            write('transcript-template.txt', 'TEMPLATE ONLY — NO TRANSCRIPTION HAS BEEN GENERATED\n\nSpeaker 1\n0:00\n[Spoken words appear here after transcription.]\n\nSpeaker 2\n0:05\n[Next speaker turn.]\n')
        write('README.txt', 'NOTAVRA LOCAL MEETING COPY\n\nAudio files are copies of your uploaded recordings.\ntranscript.txt contains current saved text when available; timestamps can be approximate for imported text.\ntranscript-template.txt is only a format example, never a completed transcript.\nmeeting.json records source revisions, imported provenance and processing state.\n\nThese files update automatically while Notavra is running. Edit the transcript in Notavra; generated text files are overwritten on updates.\nCopies remain here if a meeting is deleted in the app. Remove exported copies separately according to your retention policy.\n')
        write('meeting.json', json.dumps({'meeting_id': ident, 'title': meeting['title'], 'date': meeting['date'],
              'revision': meeting['revision'], 'recordings': recordings, 'jobs': data['jobs'],
              'updated': time.time(), 'approved': False}, ensure_ascii=False, indent=2))
        with transaction() as c:
            c.execute("UPDATE meeting_file_exports SET state='ready',fingerprint=?,error=NULL,updated=? WHERE meeting_id=?",
                      (fingerprint, time.time(), ident))


def sync_enabled():
    with transaction() as c:
        ids = [r[0] for r in c.execute('SELECT meeting_id FROM meeting_file_exports')]
    for ident in ids:
        try:
            sync_one(ident)
        except Timeout:
            continue
        except Exception as exc:
            # Keep detailed content and system paths out of generic logs.
            with transaction() as c:
                c.execute("UPDATE meeting_file_exports SET state='error',error=? WHERE meeting_id=?",
                          (type(exc).__name__, ident))
