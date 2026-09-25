import json
import wave
from types import SimpleNamespace

import numpy as np
import pytest

from services.api.progress import ProgressReporter
from services.worker.asr_chunks import transcribe_chunks
from services.worker.settings import load_settings


def setup_audio(tmp_path):
    audio = tmp_path / 'synthetic.wav'
    with wave.open(str(audio), 'wb') as source:
        source.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        for second in range(65):
            source.writeframes(np.full(16000, second, dtype='<i2').tobytes())
    settings = load_settings().asr.model_copy(update={'checkpoint_seconds': 30})
    return {'audio': str(audio), 'run_dir': str(tmp_path), 'config': {'device': 'cpu'}}, settings


class Recognizer:
    """Deterministic timestamp fixture; tests chunk ownership, not acoustic quality."""
    def __init__(self, fail_at=None):
        self.calls = []
        self.fail_at = fail_at

    def transcribe(self, samples, **kwargs):
        origin = round(float(samples[0]) * 32768)
        self.calls.append((origin, len(samples)))
        if len(self.calls) == self.fail_at:
            raise RuntimeError('simulated_worker_loss')
        result = []
        for second in range(len(samples) // 16000):
            word = SimpleNamespace(start=second + 0.2, end=second + 0.8, word=f' word{origin + second}')
            result.append(SimpleNamespace(start=word.start, end=word.end, text=word.word,
                                          words=[word], no_speech_prob=0, avg_logprob=-0.1))
        return iter(result), SimpleNamespace(language='en')


def test_interruption_resumes_only_durable_chunks_with_bounded_reads(tmp_path):
    spec, settings = setup_audio(tmp_path)
    first = Recognizer(fail_at=2)
    with pytest.raises(RuntimeError, match='simulated_worker_loss'):
        transcribe_chunks(first, spec, settings, ProgressReporter(tmp_path, 'whisper'))
    assert len(list((tmp_path / 'whisper-checkpoints').glob('*/*.json'))) == 1
    resumed = Recognizer()
    result = transcribe_chunks(resumed, spec, settings, ProgressReporter(tmp_path, 'whisper'))
    assert result['reused_chunks'] == 1 and result['chunk_count'] == 3
    assert [origin for origin, _ in resumed.calls] == [28, 58]
    assert max(count for _, count in first.calls + resumed.calls) <= 34 * 16000
    assert [s['text'] for s in result['segments']] == [f' word{i}' for i in range(65)]
    assert [s['start'] for s in result['segments']] == [i * 16000 + 3200 for i in range(65)]


def test_corrupt_checkpoint_and_changed_audio_are_not_reused(tmp_path):
    spec, settings = setup_audio(tmp_path)
    original = transcribe_chunks(Recognizer(), spec, settings, ProgressReporter(tmp_path, 'whisper'))
    path = next((tmp_path / 'whisper-checkpoints').glob('*/00000001.json'))
    corrupt = json.loads(path.read_text())
    corrupt['payload']['segments'][0]['text'] = 'corrupted text'
    path.write_text(json.dumps(corrupt))
    repair = Recognizer()
    result = transcribe_chunks(repair, spec, settings, ProgressReporter(tmp_path, 'whisper'))
    assert result['reused_chunks'] == 2 and len(repair.calls) == 1
    assert result['segments'] == original['segments']
    changed = settings.model_copy(update={'beam_size': settings.beam_size + 1})
    result = transcribe_chunks(Recognizer(), spec, changed, ProgressReporter(tmp_path, 'whisper'))
    assert result['reused_chunks'] == 0
    with open(spec['audio'], 'r+b') as audio:
        audio.seek(-2, 2)
        audio.write(b'\x01\x00')
    result = transcribe_chunks(Recognizer(), spec, settings, ProgressReporter(tmp_path, 'whisper'))
    assert result['reused_chunks'] == 0


def test_overlap_word_ownership_retains_raw_boundary_evidence():
    from services.worker.asr_chunks import owned_segments
    words = [SimpleNamespace(start=29.2, end=29.8, word=' один'), SimpleNamespace(start=30.2, end=30.8, word=' cuvânt')]
    segment = SimpleNamespace(start=29.2, end=30.8, text=' один cuvânt', words=words, no_speech_prob=0, avg_logprob=-0.1)
    left = owned_segments([segment], 0, 0, 30*16000, 60*16000, True)
    right = owned_segments([segment], 0, 30*16000, 60*16000, 60*16000, True)
    assert [s['text'] for s in left+right] == [' один', ' cuvânt']
    assert all(s['raw']['text'] == ' один cuvânt' and s['raw']['boundary_review'] for s in left+right)
