import sys
import wave
from types import SimpleNamespace

from services.worker.settings import load_settings
from services.worker.stage import whisper


def test_code_switches_are_preserved_without_translation_or_recording_wide_label(tmp_path, monkeypatch):
    observed = {}
    texts = ['Обсудим cererea de ofertă сегодня.', 'Termenul este mâine, но пока это предложение.']

    class Model:
        def __init__(self, *args, **kwargs):
            observed['local'] = kwargs['local_files_only']

        def transcribe(self, audio, **kwargs):
            observed.update(kwargs)
            return iter([
                SimpleNamespace(start=i, end=i+1, text=text, words=[SimpleNamespace(start=i, end=i+1, word=text)], no_speech_prob=0, avg_logprob=-0.1)
                for i, text in enumerate(texts)
            ]), SimpleNamespace(duration=2, language='ru')

    monkeypatch.setitem(sys.modules, 'faster_whisper', SimpleNamespace(WhisperModel=Model))
    audio = tmp_path / 'synthetic-contract-only.wav'
    with wave.open(str(audio), 'wb') as source:
        source.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        source.writeframes(b'\0\0' * 32000)
    result = whisper({'audio': str(audio), 'run_dir': str(tmp_path), 'config': {'device': 'cpu', 'inference': load_settings().model_dump()}})
    assert observed['local'] and observed['multilingual']
    assert observed['language'] is None and observed['task'] == 'transcribe'
    assert [s['text'] for s in result['segments']] == texts
    assert result['segments'][1]['words'][0]['start'] == 16000
    assert 'not a language label for every word' in result['language_scope']
    # This tests adapter preservation, not acoustic accuracy; no fabricated inference.


def test_optional_comparison_does_not_skip_speech_without_numbers(tmp_path, monkeypatch):
    from contextlib import nullcontext
    from services.worker import optional

    monkeypatch.setattr(optional.config, 'DATA', tmp_path)
    (tmp_path / 'jobs/job').mkdir(parents=True)
    audio = tmp_path / 'synthetic.wav'
    with wave.open(str(audio), 'wb') as source:
        source.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        source.writeframes(b'\1\0' * 80000)
    monkeypatch.setattr(optional, 'transaction', lambda: nullcontext(None))
    captured = []

    def run(job, stage, spec):
        captured.extend(spec['clips'])
        return {'hypotheses': []}

    optional.optional_stages(
        {'id': 'job', 'meeting_id': 'meeting'},
        {'config': {'parakeet': True, 'inference': load_settings().model_dump()}},
        {'samples': 80000, 'path': str(audio)},
        [{'id': 'a', 'text': 'Обсудим cererea сегодня.', 'start': 0, 'end': 40000},
         {'id': 'b', 'text': 'Mulțumesc pentru explicație.', 'start': 40000, 'end': 80000}], run,
    )
    assert [clip['segment_id'] for clip in captured] == ['a', 'b']
    assert captured[0]['start'] == 0 and captured[-1]['end'] == 80000
    for clip in captured:
        with wave.open(str(clip['path']), 'rb') as source:
            assert source.getnframes() == clip['end'] - clip['start']
            assert source.readframes(source.getnframes()) == b'\1\0' * source.getnframes()
