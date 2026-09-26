import json
import wave
from types import SimpleNamespace

from services.api.progress import ProgressReporter
from services.worker.gap_recovery import recover_gaps, windows
from services.worker.settings import load_settings


def test_gap_windows_cover_primary_source_with_bounded_context():
    spans = list(windows(16000, 66 * 16000, 70 * 16000, 20, 2))
    assert spans[0]['primary_start'] == 16000
    assert spans[-1]['primary_end'] == 66 * 16000
    assert all(a['primary_end'] == b['primary_start'] for a, b in zip(spans, spans[1:]))
    assert all(0 <= s['source_start'] < s['source_end'] <= 70 * 16000 for s in spans)
    assert max(s['source_end'] - s['source_start'] for s in spans) <= 24 * 16000


def test_empty_gap_retries_are_bounded_checkpointed_and_never_fused(tmp_path):
    audio = tmp_path / 'source.wav'
    with wave.open(str(audio), 'wb') as writer:
        writer.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        writer.writeframes(b'\1\0' * 30 * 16000)
    seen = []

    class Model:
        def transcribe(self, paths, **kwargs):
            with wave.open(paths[0]) as reader:
                frames = reader.getnframes()
                assert reader.readframes(frames) == b'\1\0' * frames
            seen.append(frames)
            return [SimpleNamespace(text='' if len(seen) == 1 else 'Обсудим cererea.', timestamp={})]

    spec = {'audio': str(audio), 'audio_samples': 30 * 16000, 'run_dir': str(tmp_path),
            'recovery_gaps': [{'start': 2 * 16000, 'end': 22 * 16000}], 'config': {'device': 'cpu'}}
    settings = load_settings().optional
    progress = ProgressReporter(tmp_path, 'parakeet')
    first = recover_gaps(Model(), spec, settings, progress)
    assert len(first) == 3 and first[0]['text'] == ''
    assert [r['attempt'] for r in first] == ['initial', 'short_retry', 'short_retry']
    assert all(r['text'] == 'Обсудим cererea.' for r in first[1:])
    assert not list((tmp_path / 'gap-recovery').rglob('*.wav'))
    assert recover_gaps(Model(), spec, settings, progress) == first and len(seen) == 3
    # One corrupt checkpoint is recomputed, without discarding other completed work.
    path = next((tmp_path / 'gap-recovery').rglob('*short_retry.json'))
    path.write_text('{broken', encoding='utf-8')
    assert len(recover_gaps(Model(), spec, settings, progress)) == 3 and len(seen) == 4
    data = json.loads((tmp_path / 'progress.json').read_text())
    assert data['completed'] == data['total'] == 1
    assert 'segments' not in first[0]  # These are proposals, never a replacement transcript.
