import pytest

from scripts import register_speech_runtime as registration


@pytest.mark.parametrize('previous', [None, b'{"previous": "registration"}'])
def test_failed_package_validation_restores_registration(tmp_path, monkeypatch, previous):
    marker = tmp_path/'notavra-speech-runtime.json'
    if previous is not None:
        marker.write_bytes(previous)
    monkeypatch.setattr(registration.sys, 'platform', 'linux')
    monkeypatch.setattr(registration.sys, 'prefix', str(tmp_path))
    monkeypatch.setattr(registration, 'fingerprint', lambda name: 'fixture fingerprint')

    def mismatch(name):
        raise RuntimeError('speech_package_mismatch')

    monkeypatch.setattr(registration, 'verify_runtime', mismatch)
    with pytest.raises(RuntimeError, match='speech_package_mismatch'):
        registration.register('vibevoice')
    assert (marker.read_bytes() if marker.exists() else None) == previous
