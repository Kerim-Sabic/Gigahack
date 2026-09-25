import hashlib
import json

from services.worker.supervisor import cached_stage_output


def test_stage_cache_rejects_partial_corrupt_or_stale_artifacts(tmp_path):
    target, receipt = tmp_path / 'output.json', tmp_path / 'receipt.json'
    payload = b'{"segments": []}'
    target.write_bytes(payload)
    assert cached_stage_output(target, receipt, 'input') is None
    record = {'input_hash': 'input', 'output_hash': hashlib.sha256(payload).hexdigest()}
    receipt.write_text(json.dumps(record))
    assert cached_stage_output(target, receipt, 'input') == {'segments': []}
    assert cached_stage_output(target, receipt, 'changed input') is None
    target.write_bytes(b'{"segments": [{"text": "corrupted"}]}')
    assert cached_stage_output(target, receipt, 'input') is None
    target.write_bytes(payload)
    receipt.write_text('{"input_hash":')
    assert cached_stage_output(target, receipt, 'input') is None


def test_stage_cache_requires_a_mapping_output_even_with_matching_hash(tmp_path):
    target, receipt = tmp_path / 'output.json', tmp_path / 'receipt.json'
    target.write_bytes(b'null')
    receipt.write_text(json.dumps({'input_hash': 'input', 'output_hash': hashlib.sha256(b'null').hexdigest()}))
    assert cached_stage_output(target, receipt, 'input') is None
