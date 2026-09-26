"""Exact package admission for isolated speech runtimes, including source revisions."""

import hashlib
import importlib.metadata as metadata
import json
import platform
import re
import sys
from pathlib import Path

from services.api.config import ROOT


def lock_path(name='qwen-original'):
    if name not in {'qwen-original','nemotron3','vibevoice'}:
        raise ValueError('unknown_speech_runtime')
    return ROOT / f'manifests/speech-runtime/{name}.lock.txt'


def fingerprint(name='qwen-original'):
    inventory = lock_path(name).with_name(f'{name}-packages.json')
    return hashlib.sha256(lock_path(name).read_bytes()+inventory.read_bytes()).hexdigest()


def prepared_python(prefix, name='qwen-original'):
    root = Path(prefix)
    if sys.platform != 'linux' or not prefix or not root.is_absolute():
        raise RuntimeError('speech_requires_prepared_linux_runtime')
    try:
        marker = json.loads((root / 'notavra-speech-runtime.json').read_text())
        if (marker['fingerprint'] != fingerprint(name) or marker['runtime'] != name or marker['prefix'] != str(root.resolve())
                or not (root/'bin/python').is_file()):
            raise ValueError('stale_registration')
    except (OSError, ValueError, KeyError) as exc:
        raise RuntimeError('speech_runtime_not_prepared') from exc
    return str(root/'bin/python')


def verify_runtime(name='qwen-original'):
    prepared_python(sys.prefix,name)
    if sys.version_info[:2] != (3, 12) or platform.machine() != 'x86_64':
        raise RuntimeError('speech_requires_linux_x86_64_python312')
    def normalize(name):
        return re.sub(r'[-_.]+', '-', name).lower()

    inventory = json.loads(lock_path(name).with_name(f'{name}-packages.json').read_text())['packages']
    expected = {normalize(item['name']):item['version'] for item in inventory}
    actual = {normalize(dist.metadata['Name']): dist.version for dist in metadata.distributions()}
    if expected != actual:
        raise RuntimeError('speech_package_mismatch: '+', '.join(sorted(
            name for name in expected.keys() | actual.keys() if expected.get(name) != actual.get(name))))
    for item in inventory:
        if item.get('direct_url'):
            origin = json.loads(metadata.distribution(item['name']).read_text('direct_url.json') or '{}')
            if origin != item['direct_url']:
                raise RuntimeError('speech_package_source_revision_mismatch')
    return {'fingerprint': fingerprint(name), 'prefix': sys.prefix, 'packages': len(actual),'runtime':name}
