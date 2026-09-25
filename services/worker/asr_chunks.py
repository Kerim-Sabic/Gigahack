"""Bounded PCM reads and durable, input-bound transcription checkpoints."""

import hashlib
import json
from pathlib import Path

import numpy as np

from services.api.audio import atomic_write, sha
from services.api.pcm import Reader
from services.api.db import canonical
from services.api.provenance import runtime_identity


RATE = 16000


def owned_segments(result, offset, start, end, total, multilingual, observe=lambda _: None):
    """Use source word midpoint ownership, retaining the full raw hypothesis for review."""
    segments = []
    for segment in result:
        observe(min(end, offset + round(segment.end * RATE)) / RATE)
        if segment.no_speech_prob > 0.8 and segment.avg_logprob < -1:
            continue
        words = [
            dict(start=max(0, offset + round(w.start * RATE)),
                 end=min(total, offset + round(w.end * RATE)), text=w.word)
            for w in (segment.words or [])
        ]
        selected = [w for w in words if start <= (w['start'] + w['end']) / 2 < end]
        absolute_start = max(0, offset + round(segment.start * RATE))
        absolute_end = min(total, offset + round(segment.end * RATE))
        if words and not selected:
            continue
        if not words and not start <= (absolute_start + absolute_end) / 2 < end:
            continue
        text = segment.text if len(selected) == len(words) else ''.join(w['text'] for w in selected)
        if not text.strip():
            continue
        boundary = absolute_start < start or absolute_end > end
        segments.append(dict(
            start=selected[0]['start'] if selected else absolute_start,
            end=selected[-1]['end'] if selected else absolute_end,
            text=text, words=selected,
            raw=dict(text=segment.text, avg_logprob=segment.avg_logprob,
                     no_speech_prob=segment.no_speech_prob,
                     language_policy='per_decoding_window' if multilingual else 'recording_level',
                     chunk_start=start, chunk_end=end,
                     boundary_review=boundary,
                     boundary_policy='source_word_midpoint; inspect boundary audio when uncertain'),
        ))
    return segments


def transcribe_chunks(model, spec, settings, progress):
    audio = Path(spec['audio'])
    # Hash the actual file; a caller-supplied digest alone cannot validate a checkpoint.
    identity = dict(audio_sha256=sha(audio), settings=settings.model_dump(),
                    device=spec['config']['device'], oom_retry=spec['config'].get('oom_retry', False),
                    implementation=runtime_identity())
    key = hashlib.sha256(canonical(identity).encode()).hexdigest()
    directory = Path(spec['run_dir']) / 'whisper-checkpoints' / key
    directory.mkdir(parents=True, exist_ok=True)
    segments, languages = [], []
    reused = 0
    with Reader(audio) as source:
        if (source.getframerate(), source.getnchannels(), source.getsampwidth()) != (RATE, 1, 2):
            raise ValueError('asr_requires_canonical_pcm16_mono_16khz')
        total = source.getnframes()
        if total <= 0:
            raise ValueError('empty_audio')
        progress.begin('transcribing', total / RATE, 'seconds')
        step, overlap = settings.checkpoint_seconds * RATE, settings.overlap_seconds * RATE
        for index, start in enumerate(range(0, total, step)):
            end = min(total, start + step)
            path = directory / f'{index:08d}.json'
            checkpoint = None
            if path.exists():
                try:
                    candidate = json.loads(path.read_text(encoding='utf-8'))
                    payload = candidate['payload']
                    if (candidate['sha256'] == hashlib.sha256(canonical(payload).encode()).hexdigest()
                            and payload['key'] == key and payload['start'] == start and payload['end'] == end):
                        checkpoint = payload
                except (OSError, ValueError, KeyError, TypeError):
                    pass  # A partial/corrupt checkpoint is recomputed; it is never published.
            if checkpoint is None:
                offset, stop = max(0, start - overlap), min(total, end + overlap)
                source.setpos(offset)
                pcm = source.readframes(stop - offset)
                if len(pcm) != (stop - offset) * 2:
                    raise ValueError('truncated_canonical_audio')
                samples = np.frombuffer(pcm, dtype='<i2').astype(np.float32) / 32768.0
                result, info = model.transcribe(
                    samples, language=None, task='transcribe', beam_size=settings.beam_size,
                    word_timestamps=True, condition_on_previous_text=settings.condition_on_previous_text,
                    multilingual=settings.multilingual, vad_filter=settings.vad_filter,
                    chunk_length=settings.retry_window_seconds if spec['config'].get('oom_retry') else settings.decode_window_seconds,
                )
                checkpoint = dict(key=key, start=start, end=end, language=info.language,
                                  segments=owned_segments(result, offset, start, end, total, settings.multilingual,
                                      lambda done: progress.advance(max(progress.completed, done))))
                envelope = dict(payload=checkpoint, sha256=hashlib.sha256(canonical(checkpoint).encode()).hexdigest())
                atomic_write(path, canonical(envelope).encode())
                del samples, pcm
            else:
                reused += 1
                # Restored work is not new throughput; do not promise an implausibly short ETA.
                progress.begin("transcribing", total / RATE, "seconds", initial_completed=end / RATE)
            segments.extend(checkpoint['segments'])
            languages.append(checkpoint['language'])
            progress.advance(end / RATE, force=True)
    return dict(segments=segments, language=languages[0], duration=total / RATE,
                language_scope='initial detection only; not a language label for every word',
                multilingual=settings.multilingual, checkpoint_key=key, reused_chunks=reused,
                chunk_count=len(languages), chunk_initial_languages=languages)
