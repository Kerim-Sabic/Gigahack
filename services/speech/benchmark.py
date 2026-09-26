"""Bounded benchmark batches; references never enter inference inputs."""

import json
from pathlib import Path

from services.api.audio import atomic_write, sha
from services.api.progress import ProgressReporter
from .baselines import WhisperEngine, ParakeetEngine


def baseline_batch(spec, name):
    cases = spec['benchmark_cases']
    if not isinstance(cases,list) or not 1 <= len(cases) <= 32:
        raise ValueError('benchmark_requires_one_to_32_cases')
    for case in cases:
        if sha(case['audio']) != case['canonical_audio_hash']:
            raise ValueError('benchmark_audio_changed')
    progress = ProgressReporter(spec['run_dir'],name)
    if name == 'vibevoice':
        from services.worker.settings import settings_for
        from .vibevoice import VibeVoiceEngine

        engine = VibeVoiceEngine(**settings_for(spec).vibevoice.model_dump(exclude={'runtime_prefix'}))
    elif name == 'whisper':
        engine = WhisperEngine(precision=spec.get('benchmark_precision','float16'))
    elif name == 'parakeet':
        engine = ParakeetEngine()
    else:
        raise ValueError('unknown_benchmark_engine')
    progress.begin('transcribing',len(cases),'clips')
    outputs=[]
    for index,case in enumerate(cases):
        window=case['speech_window']
        try:
            result=engine.transcribe(case['audio'],window['start'],window['end']).model_dump()
        except RuntimeError as exc:
            if hasattr(exc, 'evidence'):
                artifact = f'case-{index:03d}-failed.json'
                atomic_write(Path(spec['run_dir'])/artifact,json.dumps(exc.evidence,ensure_ascii=False).encode())
                outputs.append({'id':case['id'],'result':None,'failure':{'reason':str(exc),'artifact':artifact}})
                progress.advance(index+1,force=True)
                continue  # Invalid model output fails this case, not the remaining reference tests.
            raise
        atomic_write(Path(spec['run_dir'])/f'case-{index:03d}.json',json.dumps(result,ensure_ascii=False).encode())
        outputs.append({'id':case['id'],'result':result})
        progress.advance(index+1,force=True)
    return {'cases':outputs,'scope':'independent source clips; no transcript fusion or approval'}
