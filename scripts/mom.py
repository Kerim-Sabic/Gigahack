"""Cohesive offline runtime and online preparation CLI."""
import argparse
import hashlib
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import httpx
import psutil

from services.api import config
from services.api.db import migrate


def doctor():
    gpu = None
    try:
        gpu = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,driver_version', '--format=csv'],
                             capture_output=True, text=True, timeout=15, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    ports = {}
    for port in [8765, 8081, 1025, 8025]:
        with socket.socket() as s:
            ports[port] = 'occupied' if s.connect_ex(('127.0.0.1', port)) == 0 else 'available'
    report = {'platform': sys.platform, 'python': sys.version.split()[0], 'gpu': gpu,
              'ram_bytes': psutil.virtual_memory().total, 'disk_free_bytes': shutil.disk_usage(config.ROOT).free,
              'ffmpeg': bool(shutil.which('ffmpeg')), 'ports': ports,
              'models': {n: (config.MODELS / n).exists() for n in ['whisper', 'qwen']},
              'network_observation': 'not measured', 'target_laptop': 'not qualified'}
    print(json.dumps(report, indent=2))
    return report


def verify_assets():
    manifest = config.ROOT / 'manifests/models.lock.json'
    if not manifest.exists():
        raise SystemExit('Missing model manifest: run prepare-models online.')
    for name, data in json.loads(manifest.read_text()).items():
        for filename, expected in data['files'].items():
            path = config.MODELS / name / filename
            if not path.exists():
                raise SystemExit(f'Missing prepared asset: {name}/{filename}')
            with path.open('rb') as f:
                actual = hashlib.file_digest(f, 'sha256').hexdigest()
            if actual != expected:
                raise SystemExit(f'Asset checksum mismatch: {name}/{filename}')
    print('All prepared model checksums verified.')


def start():
    config.init_dirs()
    if not (config.ROOT / 'apps/web/dist/index.html').exists():
        raise SystemExit('Frontend not prepared. Run npm ci and npm run build in apps/web.')
    pidfile = config.DATA / 'processes.json'
    if pidfile.exists():
        for p in json.loads(pidfile.read_text()):
            if psutil.pid_exists(p['pid']):
                raise SystemExit('Recorded service is running. Use stop before starting again.')
    migrate()
    mail = list((config.ROOT / '.runtime/tools/mailpit').rglob('mailpit.exe' if os.name == 'nt' else 'mailpit'))
    if not mail:
        raise SystemExit('Mailpit is missing. Run prepare-tools while online.')
    commands = [
        [str(mail[0]), '--listen', '127.0.0.1:8025', '--smtp', '127.0.0.1:1025', '--database', str(config.DATA / 'mailpit.sqlite')],
        [sys.executable, '-m', 'uvicorn', 'services.api.main:app', '--host', '127.0.0.1', '--port', '8765'],
        [sys.executable, '-m', 'services.worker.supervisor'],
    ]
    records = []
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    try:
        for name, command in zip(['mailpit', 'api', 'worker'], commands, strict=True):
            with (config.DATA / f'{name}.log').open('ab') as log:
                p = subprocess.Popen(command, cwd=config.ROOT, stdout=log, stderr=log,
                                     creationflags=flags, start_new_session=os.name != 'nt')
            records.append({'pid': p.pid, 'created': psutil.Process(p.pid).create_time(), 'name': name})
        pidfile.write_text(json.dumps(records))
        for _ in range(30):
            try:
                if httpx.get('http://127.0.0.1:8765/api/v1/system/health', trust_env=False).status_code == 200:
                    print('Secure MOM ready: http://127.0.0.1:8765 ; Mailpit: http://127.0.0.1:8025')
                    return
            except httpx.HTTPError:
                pass
            time.sleep(1)
        raise RuntimeError('Startup readiness timed out; see local logs.')
    except BaseException:
        stop()
        raise


def stop():
    from services.worker.supervisor import kill_tree
    path = config.DATA / 'processes.json'
    if path.exists():
        for record in reversed(json.loads(path.read_text())):
            try:
                p = psutil.Process(record['pid'])
                if abs(p.create_time()-record['created']) < .01:
                    kill_tree(p.pid)
            except psutil.NoSuchProcess:
                pass
        path.unlink()
    print('Managed services stopped; recordings and database retained.')


def backup(destination):
    target = Path(destination).resolve()
    if target.exists():
        raise SystemExit('Backup destination must not exist.')
    # Require stopped services so audio/manifests and SQLite share a consistent boundary.
    if (config.DATA / 'processes.json').exists():
        raise SystemExit('Stop managed services before backup.')
    target.mkdir(parents=True)
    with sqlite3.connect(config.DATA / 'app.sqlite') as source, sqlite3.connect(target / 'app.sqlite') as dest:
        source.backup(dest)
    for name in ['audio', 'jobs', 'exports', 'proofs']:
        shutil.copytree(config.DATA / name, target / name, dirs_exist_ok=True)
    (target / 'backup.json').write_text(json.dumps({'version': 1, 'original_data_root': str(config.DATA.resolve())}))
    print('Consistent stopped backup created.')


def restore(source):
    source = Path(source).resolve()
    if (config.DATA / 'app.sqlite').exists():
        raise SystemExit('Restore requires a new empty MOM_DATA directory; existing data is never overwritten.')
    metadata = json.loads((source / 'backup.json').read_text())
    shutil.copytree(source, config.DATA, dirs_exist_ok=True)
    with sqlite3.connect(config.DATA / 'app.sqlite') as c:
        for table, column in [('assets', 'path'), ('chunks', 'path')]:
            c.execute(f'UPDATE {table} SET {column}=replace({column},?,?)', (metadata['original_data_root'], str(config.DATA.resolve())))
        assert c.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    print('Backup restored; database integrity check passed.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['doctor', 'prepare-models', 'prepare-tools', 'verify-assets', 'start', 'stop', 'test', 'backup', 'restore', 'qualify-target'])
    parser.add_argument('--path')
    args = parser.parse_args()
    if args.command == 'doctor':
        doctor()
    elif args.command == 'prepare-models':
        from scripts.prepare_models import prepare
        prepare()
    elif args.command == 'prepare-tools':
        from scripts.prepare_tools import prepare
        prepare()
    elif args.command == 'verify-assets':
        verify_assets()
    elif args.command == 'start':
        start()
    elif args.command == 'stop':
        stop()
    elif args.command == 'test':
        raise SystemExit(subprocess.call([sys.executable, '-m', 'pytest', '-q', '--basetemp', str(config.DATA / 'test-temp')]))
    elif args.command == 'backup':
        backup(args.path)
    elif args.command == 'restore':
        restore(args.path)
    else:
        from scripts.qualify import qualify
        qualify(args.path)


if __name__ == '__main__':
    main()
