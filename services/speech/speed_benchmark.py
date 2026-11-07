"""Explicit speed experiment. Never writes results into the meeting transcript."""
from concurrent.futures import ThreadPoolExecutor
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

from services.api.audio import atomic_write, sha
from services.api.config import MODELS, ROOT
from services.api.progress import ProgressReporter


def run(spec):
    from faster_whisper import WhisperModel, BatchedInferencePipeline
    from faster_whisper.audio import decode_audio

    options = spec['speed_benchmark']
    if options['precision'] not in ('float16', 'int8_float16') or options['batch_size'] not in (8, 16, 32, 64):
        raise ValueError('unsupported_speed_profile')
    if sha(spec['audio']) != spec['input_sha256']:
        raise ValueError('benchmark_input_changed')
    handles = []
    if os.name == 'nt':
        for folder in [ROOT / '.runtime/tools/llama', *Path(sys.prefix).glob('Lib/site-packages/nvidia/*/bin')]:
            if folder.is_dir():
                handles.append(os.add_dll_directory(str(folder)))
    started = time.perf_counter()
    audio = decode_audio(spec['audio'], sampling_rate=16000)
    decode_seconds = time.perf_counter() - started
    duration = len(audio) / 16000
    clips = [{'start': start, 'end': min(start + 30 * 16000, len(audio))} for start in range(0, len(audio), 30 * 16000)]
    progress = ProgressReporter(spec['run_dir'], 'whisper')
    started = time.perf_counter()
    model = WhisperModel(str(MODELS / 'whisper'), device='cuda', device_index=[0,1] if options['gpu']==-1 else 0,
                         compute_type=options['precision'], local_files_only=True, num_workers=2 if options['gpu']==-1 else 1)
    load_seconds = time.perf_counter() - started
    def transcribe_part(part, offset):
        pipeline = BatchedInferencePipeline(model)
        part_clips = [{'start': start / 16000, 'end': min(start + 30 * 16000, len(part)) / 16000} for start in range(0, len(part), 30 * 16000)]
        segments, _ = pipeline.transcribe(part, language='ro', task='transcribe', beam_size=1, best_of=1,
            temperature=0, condition_on_previous_text=False, word_timestamps=False, without_timestamps=True,
            vad_filter=False, clip_timestamps=part_clips, batch_size=options['batch_size'], multilingual=False)
        return [{'start':segment.start+offset,'end':segment.end+offset,'text':segment.text} for segment in segments]

    runs = []
    for repeat in range(3):
        progress.begin('transcribing', duration, 'seconds')
        started = time.perf_counter()
        if options['gpu']==-1:
            midpoint = ((len(clips)+1)//2)*30*16000
            with ThreadPoolExecutor(max_workers=2) as executor:
                first=executor.submit(transcribe_part,audio[:midpoint],0)
                second=executor.submit(transcribe_part,audio[midpoint:],midpoint/16000)
                saved=first.result()+second.result()
        else:
            saved=transcribe_part(audio,0)
        elapsed = time.perf_counter() - started
        if not saved:
            raise RuntimeError('benchmark_produced_no_text')
        runs.append({'run':repeat + 1, 'seconds':elapsed,'speed_multiple':duration / elapsed,
                     'segments':len(saved),'characters':sum(len(s['text']) for s in saved),
                     'last_segment_end':saved[-1]['end']})
        atomic_write(Path(spec['run_dir']) / f'transcript-{repeat+1}.json', json.dumps(saved,ensure_ascii=False).encode())
        progress.advance(duration,force=True)
    return {'audio_seconds':duration, 'decode_seconds':decode_seconds,'model_load_seconds':load_seconds,
            'cold_core_seconds':decode_seconds+load_seconds+runs[0]['seconds'], 'runs':runs,
            'profile':options,'fixed_chunks':len(clips),'input_samples':len(audio),
            'coverage':'Entire input in contiguous 30-second windows, no VAD removal',
            'versions':{name:importlib.metadata.version(name) for name in ('faster-whisper','ctranslate2','av')},
            'accuracy':'Not evaluated. Romanian forced; greedy decoding, no word alignment, no LLM, no diarization.'}
