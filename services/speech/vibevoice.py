"""Experimental local VibeVoice benchmark; one worker reserves both GPUs."""

import importlib.metadata
import json
import math
import time

from .baselines import audio_window, verified_manifest
from .context import ContextBuilder
from .contracts import ASREngine, ASRResult

NON_SPEECH = frozenset({'[Silence]', '[Environmental Sounds]'})


class InvalidVibeVoiceOutput(RuntimeError):
    def __init__(self, reason, evidence):
        super().__init__(reason)
        self.evidence = evidence


def parse_segments(text, duration):
    """Validate structured speech without accepting raw JSON as spoken text."""
    value = text.strip()
    if value.startswith('assistant\n'):
        value = value[len('assistant\n'):].strip()
    try:
        rows = json.loads(value)
    except (ValueError, TypeError) as exc:
        raise ValueError('vibevoice_invalid_json') from exc
    if not isinstance(rows, list):
        raise ValueError('vibevoice_requires_segment_array')
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('Content'), str):
            raise ValueError('vibevoice_invalid_content')
        if row.get('Speaker') is None and row['Content'] in NON_SPEECH:
            pass  # Publisher-style non-speech events carry no person identity.
        elif type(row.get('Speaker')) is not int or row['Speaker'] < 0:
            raise ValueError('vibevoice_invalid_anonymous_speaker')
        for key in ('Start', 'End'):
            if type(row.get(key)) not in (int, float) or not math.isfinite(row[key]):
                raise ValueError('vibevoice_invalid_segment_time')
        # Rounding can place the last model timestamp just beyond EOF. Retain it
        # in raw evidence, but never coerce it into a valid source-clock label.
        if not 0 <= row['Start'] < row['End'] <= duration:
            raise ValueError('vibevoice_segment_outside_source')
    return rows


def device_map(layer_count):
    if type(layer_count) is not int or layer_count < 2:
        raise ValueError('invalid_decoder_layers')
    mapping = {
        'model.acoustic_tokenizer_encoder': 0,
        'model.semantic_tokenizer_encoder': 0,
        'model.multi_modal_projector': 0,
        'model.language_model.embed_tokens': 0,
        'model.language_model.norm': 1,
        'lm_head': 1,
    }
    # Leave more room for the two audio encoders on GPU 0.
    first = layer_count // 3
    mapping.update({f'model.language_model.layers.{i}': 0 if i < first else 1 for i in range(layer_count)})
    return mapping


class VibeVoiceEngine(ASREngine):
    def __init__(self, *, max_new_tokens=2048, context_characters=1024, seed=42):
        if type(max_new_tokens) is not int or not 32 <= max_new_tokens <= 4096:
            raise ValueError('invalid_vibevoice_output_budget')
        self.manifest, path = verified_manifest('speech-models.lock.json', 'vibevoice', 'vibevoice-asr')
        self.context = ContextBuilder(context_characters)
        self.max_new_tokens, self.seed = max_new_tokens, seed
        import torch
        from transformers import AutoProcessor, VibeVoiceAsrForConditionalGeneration

        self.torch = torch
        if torch.cuda.device_count() != 2:
            raise RuntimeError('vibevoice_benchmark_requires_two_exclusively_admitted_gpus')
        for index in range(2):
            free, _ = torch.cuda.mem_get_info(index)
            if free < 11 * 1024**3:
                raise RuntimeError('vibevoice_requires_11_gib_free_per_device_before_loading')
            torch.cuda.reset_peak_memory_stats(index)
        configuration = json.loads((path/'config.json').read_text())
        self.mapping = device_map(configuration['text_config']['num_hidden_layers'])
        self.processor = AutoProcessor.from_pretrained(path, local_files_only=True, trust_remote_code=False)
        self.model = VibeVoiceAsrForConditionalGeneration.from_pretrained(
            path, local_files_only=True, trust_remote_code=False, use_safetensors=True,
            dtype=torch.bfloat16, device_map=self.mapping,
            attn_implementation={'text_config': 'sdpa', 'acoustic_tokenizer_encoder_config': 'eager',
                                 'semantic_tokenizer_encoder_config': 'eager'},
        ).eval()

    def supports_language(self, language):
        return language in {'ro', 'ru', 'en'}

    def health_check(self):
        return {'loaded': True, 'model': self.manifest['repo'], 'revision': self.manifest['revision'],
                'device_map': self.mapping, 'streaming': False, 'word_timestamps': False}

    def transcribe(self, audio_path, start_sample, end_sample, *, terms=(), language_hint=None):
        if language_hint is not None:
            raise ValueError('vibevoice_benchmark_does_not_force_language')
        from scipy.signal import resample_poly

        audio = audio_window(audio_path, start_sample, end_sample)
        audio = resample_poly(audio, 3, 2)  # 16 kHz canonical clock -> native 24 kHz input.
        prompt = self.context.build(user_terms=terms)
        started = time.monotonic()
        self.torch.manual_seed(self.seed)  # Upstream acoustic encoder samples latent noise.
        self.torch.cuda.manual_seed_all(self.seed)
        inputs = self.processor.apply_transcription_request(audio=audio, prompt=prompt or None)
        inputs = inputs.to('cuda:0', self.torch.bfloat16)
        with self.torch.inference_mode():
            outputs = self.model.generate(**inputs, do_sample=False, max_new_tokens=self.max_new_tokens)
        generated = outputs[:, inputs['input_ids'].shape[1]:]
        raw = self.processor.tokenizer.batch_decode(generated, skip_special_tokens=False)[0]
        text = self.processor.tokenizer.batch_decode(generated, skip_special_tokens=True)[0]
        evidence = {'output': raw, 'token_ids': generated[0].tolist(), 'context': prompt,
                    'seed': self.seed, 'device_map': self.mapping, 'input_resample': 'scipy resample_poly 3/2',
                    'peak_gpu_memory': [{'device': i, 'allocated_bytes': self.torch.cuda.max_memory_allocated(i),
                        'reserved_bytes': self.torch.cuda.max_memory_reserved(i)} for i in range(2)]}
        eos = self.model.generation_config.eos_token_id
        eos = eos if isinstance(eos, list) else [eos]
        if generated.shape[1] >= self.max_new_tokens and int(generated[0, -1]) not in eos:
            raise InvalidVibeVoiceOutput('vibevoice_output_truncated_not_publishable', evidence)
        try:
            segments = parse_segments(text, (end_sample-start_sample)/16000)
        except ValueError as exc:
            raise InvalidVibeVoiceOutput(str(exc), evidence) from exc
        evidence['segments'] = segments
        evidence['speaker_scope'] = 'anonymous model labels local to this window; not verified identities'
        return ASRResult(engine='vibevoice', model=self.manifest['repo'], model_version=self.manifest['revision'],
            runtime='transformers '+importlib.metadata.version('transformers'), precision='bfloat16', device='cuda:0,cuda:1',
            text=' '.join(row['Content'] for row in segments if row['Content'] not in NON_SPEECH),
            start_sample=start_sample, end_sample=end_sample,
            latency_ms=(time.monotonic()-started)*1000, raw=evidence,
            unavailable=['word_timestamps', 'span_language_labels', 'calibrated_confidence', 'native_streaming'])
