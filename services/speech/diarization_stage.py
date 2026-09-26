"""Source-preserving Nemotron stage; frame evidence remains local and unreviewed."""

import time
from pathlib import Path

from services.api.audio import atomic_write, sha
from services.api.pcm import Reader
from services.api.progress import ProgressReporter
from services.api.storage import require_space
from services.worker.settings import settings_for
from .nemotron import NemotronEngine, SpeakerTurns


def nemotron_diarize(spec):
    settings = settings_for(spec).nemotron
    folder = Path(spec['run_dir'])/'nemotron-frames'
    folder.mkdir(parents=True,exist_ok=True)
    if sha(spec['audio']) != spec['canonical_audio_hash']:
        raise ValueError('diarization_source_changed')
    with Reader(Path(spec['audio'])) as reader:
        samples = reader.getnframes()
    progress = ProgressReporter(spec['run_dir'],'diarize')
    engine = NemotronEngine(mode=settings.mode)
    turns = SpeakerTurns(samples)
    progress.begin('diarizing',samples/16000,'seconds')
    started = time.monotonic()
    artifacts=[]
    for index,block in enumerate(engine.blocks(spec['audio'])):
        if block['start_frame'] != turns.frame:
            raise ValueError('diarization_frame_gap_or_overlap')
        probabilities=block.pop('probabilities')
        payload=probabilities.astype('<f4').tobytes()
        require_space(folder,len(payload))
        target=folder/f'{index:08d}.f32'
        atomic_write(target,payload)
        artifacts.append({**block,'path':str(target.relative_to(Path(spec['run_dir']))),'sha256':sha(target),
                          'shape':list(probabilities.shape),'dtype':'little_endian_float32'})
        turns.feed(probabilities > settings.threshold)
        progress.advance(min(samples,turns.frame*160)/16000,force=True)
    if turns.frame != samples//160:
        raise ValueError('diarization_incomplete_source_coverage')
    canonical_turns=turns.finish()
    return {'turns':[{'start':turn['start_sample']/16000,'end':turn['end_sample']/16000,
                      **turn} for turn in canonical_turns],
            'engine':'nemotron3','model':engine.manifest['repo'],'revision':engine.manifest['revision'],
            'mode':settings.mode,'threshold':settings.threshold,'sample_rate':16000,'frame_samples':160,
            'source_samples':samples,'scored_frames':turns.frame,'unscored_tail_samples':samples%160,
            'tail_scope':'The model scores complete 10 ms frames; a shorter EOF remainder has no invented label',
            'frame_artifacts':artifacts,
            'decode_elapsed_seconds':time.monotonic()-started,
            'peak_allocated_gpu_bytes':engine.torch.cuda.max_memory_allocated(),
            'peak_reserved_gpu_bytes':engine.torch.cuda.max_memory_reserved(),
            'speaker_identity':'anonymous arrival-order channels, maximum eight; identities and DER not measured',
            'recovery':'source survives restart; this adapter currently recomputes speaker cache after failure'}
