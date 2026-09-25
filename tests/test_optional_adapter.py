import json
import sys
from types import SimpleNamespace

from services.worker.settings import load_settings
from services.worker.stage import diarize


def test_diarization_batches_and_progress_follow_frozen_profile(tmp_path, monkeypatch):
    seen = {}

    class Pipeline:
        @classmethod
        def from_pretrained(cls, path):
            seen['model'] = path
            return cls()

        def to(self, device):
            seen['device'] = device

        def __call__(self, audio, hook):
            seen['batches'] = (self.segmentation_batch_size, self.embedding_batch_size)
            hook('segmentation', None, total=2, completed=0)
            hook('segmentation', None, total=2, completed=2)
            hook('embeddings', None, total=3, completed=0)
            hook('embeddings', None, total=3, completed=3)
            return SimpleNamespace(speaker_diarization=SimpleNamespace(itertracks=lambda **kw: [(SimpleNamespace(start=1, end=2), None, 'SPEAKER_00')]))

    monkeypatch.setitem(sys.modules, 'torch', SimpleNamespace(device=lambda value: value))
    monkeypatch.setitem(sys.modules, 'pyannote.audio', SimpleNamespace(Pipeline=Pipeline))
    settings = load_settings().model_dump()
    settings['optional']['diarization_batch_size'] = 4
    spec = {'audio': 'synthetic.wav', 'run_dir': str(tmp_path), 'config': {'device': 'cpu', 'inference': settings}}
    result = diarize(spec)
    assert seen['batches'] == (4, 4)
    assert result['turns'] == [{'start': 1, 'end': 2, 'cluster': 'SPEAKER_00'}]
    progress = json.loads((tmp_path / 'progress.json').read_text())
    assert progress['stage'] == 'diarize' and progress['completed'] == progress['total'] == 3
    spec['config']['oom_retry'] = True
    diarize(spec)
    assert seen['batches'] == (1, 1)
