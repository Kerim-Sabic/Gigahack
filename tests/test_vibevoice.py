import json

import pytest

from services.speech.vibevoice import device_map, parse_segments


def test_mixed_language_content_preserved_without_forced_language():
    row = {'Start': 0, 'End': 2, 'Speaker': 0, 'Content': 'După masă принять лекарство.'}
    assert parse_segments('assistant\n'+json.dumps([row]), 2) == [row]


def test_environmental_sound_annotation_does_not_invent_a_speaker():
    rows = [{'Start': 0, 'End': 1, 'Content': '[Environmental Sounds]'},
            {'Start': 1, 'End': 2, 'Speaker': 0, 'Content': 'Bună.'}]
    result = parse_segments(json.dumps(rows), 2)
    assert result == rows and 'Speaker' not in result[0]


@pytest.mark.parametrize('value', [
    'not JSON', '{}', '[{"Content": "missing timing"}]',
    '[{"Start": 0, "End": 3, "Speaker": 0, "Content": "outside"}]',
    '[{"Start": 0, "End": 2, "Speaker": "Dr. Smith", "Content": "identity"}]',
    '[{"Start": false, "End": 2, "Speaker": 0, "Content": "bool"}]',
    '[{"Start": 0, "End": NaN, "Speaker": 0, "Content": "nan"}]',
])
def test_unusable_model_output_cannot_become_accepted_speech(value):
    with pytest.raises(ValueError):
        parse_segments(value, 2)


def test_two_device_mapping_keeps_decoder_layers_whole():
    mapping = device_map(28)
    assert set(mapping.values()) == {0, 1}
    assert len([key for key in mapping if '.layers.' in key]) == 28
    assert mapping['model.acoustic_tokenizer_encoder'] == 0
    assert mapping['model.semantic_tokenizer_encoder'] == 0


def test_bad_output_is_retained_and_does_not_skip_remaining_cases(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from services.api.audio import sha
    from services.speech import benchmark
    from services.speech.vibevoice import InvalidVibeVoiceOutput

    audio = tmp_path/'source.wav'
    audio.write_bytes(b'fixture bytes; mocked inference does not decode them')
    calls = []

    def transcribe(*args):
        calls.append(args)
        if len(calls) == 1:
            raise InvalidVibeVoiceOutput('truncated', {'output': 'unpublishable raw output'})
        return SimpleNamespace(model_dump=lambda: {'text': 'second case survives'})

    monkeypatch.setattr(benchmark, 'ParakeetEngine', lambda: SimpleNamespace(transcribe=transcribe))
    cases = [{'id': str(i), 'audio': str(audio), 'canonical_audio_hash': sha(audio),
              'speech_window': {'start': 0, 'end': 16000}} for i in range(2)]
    result = benchmark.baseline_batch({'run_dir': str(tmp_path), 'benchmark_cases': cases}, 'parakeet')
    assert result['cases'][0]['result'] is None
    assert result['cases'][0]['failure']['reason'] == 'truncated'
    assert result['cases'][1]['result']['text'] == 'second case survives'
    assert json.loads((tmp_path/'case-000-failed.json').read_text())['output'] == 'unpublishable raw output'
