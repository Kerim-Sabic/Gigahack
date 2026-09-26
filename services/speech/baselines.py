"""Existing Whisper and Parakeet engines behind the same source-clock contract."""

import importlib.metadata
import json
import time
from dataclasses import asdict
from pathlib import Path

from services.api import config
from services.api.audio import sha
from services.api.pcm import Reader
from .contracts import ASREngine, ASRResult, Word
from .context import ContextBuilder


def audio_window(path, start, end):
    import numpy as np

    if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end or end-start > 60*16000:
        raise ValueError('requires_bounded_source_window_up_to_60_seconds')
    with Reader(Path(path)) as reader:
        if reader.getframerate() != 16000 or end > reader.getnframes():
            raise ValueError('invalid_canonical_source_window')
        reader.setpos(start)
        return np.frombuffer(reader.readframes(end-start),dtype='<i2').astype(np.float32)/32768.0


def verified_manifest(filename, key, directory):
    manifest = json.loads((config.ROOT/'manifests'/filename).read_text(encoding='utf-8'))[key]
    root = (config.MODELS/directory).resolve()
    if not root.is_relative_to(config.MODELS.resolve()):
        raise RuntimeError('model_directory_outside_prepared_assets')
    for name, expected in manifest['files'].items():
        path = root/name
        if not path.resolve().is_relative_to(root) or not path.is_file() or sha(path) != expected:
            raise RuntimeError('model_asset_missing_or_changed')
    return manifest, root


def native_words(rows, start, end, source):
    words = []
    for text, begin, finish in rows:
        first, last = start+round(begin*16000), start+round(finish*16000)
        if not start <= first < last <= end:
            # Keep native values in raw output; do not invent or clip word timing.
            return None
        words.append(Word(text=text,start_sample=first,end_sample=last,timing_source=source))
    return words


class BaselineEngine(ASREngine):
    def supports_language(self, language):
        return language in {'ro','ru','en'}

    def health_check(self):
        return {'loaded':True,'model':self.manifest['repo'],'revision':self.manifest['revision'],
                'device':self.device,'streaming':False,'word_timestamps':True}

    def result(self, text, start, end, words, raw, started, language=None, language_hint=None):
        return ASRResult(engine=self.engine,model=self.manifest['repo'],model_version=self.manifest['revision'],
                         runtime=self.runtime,precision=self.precision,device=self.device,text=text,
                         start_sample=start,end_sample=end,words=words,language=None if language_hint else language,
                         language_scope=('forced_hint_not_language_detection' if language_hint else
                                         'dominant_window_tag_not_word_labels' if language else 'unavailable'),
                         latency_ms=(time.monotonic()-started)*1000,raw={**raw,'diagnostic_language_hint':language_hint},
                         unavailable=['calibrated_confidence','span_language_labels','native_streaming'] +
                         (['word_timestamps'] if words is None else []))


class WhisperEngine(BaselineEngine):
    engine = 'whisper'

    def __init__(self, *, device='cuda:0', precision='float16', beam_size=5):
        self.manifest, path = verified_manifest('models.lock.json','whisper','whisper')
        from faster_whisper import WhisperModel

        family, index = device.split(':')
        self.model = WhisperModel(str(path),device=family,device_index=int(index),compute_type=precision,
                                  local_files_only=True,num_workers=1)
        self.device, self.precision, self.beam_size = device, precision, beam_size
        self.runtime = 'faster-whisper '+importlib.metadata.version('faster-whisper')+' / CTranslate2 '+importlib.metadata.version('ctranslate2')

    def transcribe(self, audio_path, start_sample, end_sample, *, terms=(), language_hint=None):
        if language_hint not in {None,'ro','ru','en'}:
            raise ValueError('unsupported_diagnostic_language_hint')
        audio = audio_window(audio_path,start_sample,end_sample)
        prompt = ContextBuilder().build(user_terms=terms)
        started = time.monotonic()
        generated, info = self.model.transcribe(audio,language=language_hint,task='transcribe',
            multilingual=language_hint is None,beam_size=self.beam_size,word_timestamps=True,
            condition_on_previous_text=False,vad_filter=False,initial_prompt=prompt or None)
        segments = list(generated)
        rows = [(word.word,word.start,word.end) for segment in segments for word in segment.words or []]
        words = native_words(rows,start_sample,end_sample,'whisper_native')
        return self.result(''.join(segment.text for segment in segments).strip(),start_sample,end_sample,words,
            {'segments':[asdict(segment) for segment in segments],'vad_filter':False,
             'beam_size':self.beam_size,'context':prompt},started,language=info.language,language_hint=language_hint)


class ParakeetEngine(BaselineEngine):
    engine = 'parakeet'

    def __init__(self, *, device='cuda:0'):
        self.manifest, path = verified_manifest('optional-models.lock.json','parakeet','parakeet')
        import nemo.collections.asr as nemo_asr

        self.model = nemo_asr.models.ASRModel.restore_from(str(path/'parakeet-tdt-0.6b-v3.nemo'),map_location=device).eval()
        self.device, self.precision = device, 'float32'
        self.runtime = 'nemo_toolkit '+importlib.metadata.version('nemo_toolkit')

    def transcribe(self, audio_path, start_sample, end_sample, *, terms=(), language_hint=None):
        if terms or language_hint:
            raise ValueError('parakeet_adapter_has_no_qualified_context_or_language_forcing')
        audio = audio_window(audio_path,start_sample,end_sample)
        started = time.monotonic()
        outputs = self.model.transcribe(audio=[audio],batch_size=1,return_hypotheses=True,timestamps=True,verbose=False)
        if isinstance(outputs,tuple):
            outputs = outputs[0]
        hypothesis = outputs[0]
        timestamps = hypothesis.timestamp or {}
        rows = [(item['word'],item['start'],item['end']) for item in timestamps.get('word',[])]
        words = native_words(rows,start_sample,end_sample,'parakeet_native') if rows else None
        return self.result(hypothesis.text,start_sample,end_sample,words,{'timestamps':timestamps},started)
