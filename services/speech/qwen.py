"""Official native Transformers Qwen ASR; local files and explicit source windows only."""

import importlib.metadata
import json
import time
from pathlib import Path

from services.api import config
from services.api.audio import sha
from services.api.pcm import Reader
from .contracts import ASREngine, ASRResult
from .context import ContextBuilder


class TruncatedASR(RuntimeError):
    def __init__(self, evidence):
        super().__init__("qwen_asr_output_truncated_requires_shorter_window")
        self.evidence = evidence


class QwenASREngine(ASREngine):
    LANGUAGES = {"ro", "ru", "en"}

    def __init__(self, *, device="cuda:0", max_new_tokens=1024, attention="sdpa", context_characters=1024, precision="bfloat16", backend="native"):
        if backend not in {"native", "official"}:
            raise ValueError("unknown_qwen_backend")
        self.backend = backend
        manifest = json.loads(
            (config.ROOT / "manifests/speech-models.lock.json").read_text(encoding="utf-8")
        )["qwen_asr" if backend == "native" else "qwen_asr_original"]
        self.path = config.MODELS / manifest["directory"]
        for name, expected in manifest["files"].items():
            path = self.path / name
            if (
                not path.resolve().is_relative_to(self.path.resolve())
                or not path.is_file()
                or sha(path) != expected
            ):
                raise RuntimeError("qwen_asr_local_asset_missing_or_changed")
        if not device.startswith("cuda:") or max_new_tokens < 32 or max_new_tokens > 2048:
            raise ValueError("unsupported_qwen_runtime_configuration")
        self.manifest, self.device, self.max_new_tokens = manifest, device, max_new_tokens
        self.context = ContextBuilder(context_characters)
        import torch

        self.torch = torch
        if precision not in {"bfloat16", "float16", "float32"}:
            raise ValueError("unsupported_qwen_precision")
        self.precision, self.dtype = precision, getattr(torch, precision)
        if backend == "official":
            from qwen_asr import Qwen3ASRModel

            wrapped = Qwen3ASRModel.from_pretrained(
                str(self.path), local_files_only=True, trust_remote_code=False,
                use_safetensors=True,
                dtype=self.dtype, device_map=device, attn_implementation=attention,
                max_inference_batch_size=1, max_new_tokens=max_new_tokens,
            )
            self.processor = wrapped.processor
            # The publisher wrapper delegates generation to thinker. Call it directly
            # to retain token scores and explicitly detect output-cap exhaustion.
            self.model = wrapped.model.thinker.eval()
            return
        from transformers import AutoProcessor, AutoModelForMultimodalLM

        self.processor = AutoProcessor.from_pretrained(
            self.path, local_files_only=True, trust_remote_code=False
        )
        self.model = (
            AutoModelForMultimodalLM.from_pretrained(
                self.path,
                local_files_only=True,
                trust_remote_code=False,
                use_safetensors=True,
                dtype=self.dtype,
                attn_implementation=attention,
            )
            .to(device)
            .eval()
        )

    def supports_language(self, language):
        return language in self.LANGUAGES

    def health_check(self):
        return {
            "loaded": True,
            "model": self.manifest["repo"],
            "revision": self.manifest["revision"],
            "device": self.device,
            "streaming": False,
            "word_timestamps": False,
        }

    def transcribe(self, audio_path, start_sample, end_sample, *, terms=(), language_hint=None):
        import numpy as np

        if language_hint not in {None, "ro", "ru", "en"}:
            raise ValueError("unsupported_diagnostic_language_hint")
        language_name = {"ro": "Romanian", "ru": "Russian", "en": "English"}.get(language_hint)
        if not 0 <= start_sample < end_sample or end_sample - start_sample > 60 * 16000:
            raise ValueError("qwen_requires_bounded_context_window_up_to_60_seconds")
        with Reader(Path(audio_path)) as reader:
            if (reader.getframerate(), reader.getnchannels(), reader.getsampwidth()) != (16000, 1, 2):
                raise ValueError("qwen_requires_canonical_pcm16_mono_16khz")
            if end_sample > reader.getnframes():
                raise ValueError("qwen_window_outside_source")
            reader.setpos(start_sample)
            audio = (
                np.frombuffer(reader.readframes(end_sample - start_sample), dtype="<i2").astype(np.float32)
                / 32768.0
            )
        prompt = self.context.build(user_terms=terms)
        started = time.monotonic()
        # No forced language: an overall language token must never route minority words away.
        if self.backend == "official":
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": [{"type": "audio", "audio": ""}]},
            ]
            text = self.processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
            if language_name:
                text += f"language {language_name}<asr_text>"
            inputs = self.processor(text=[text], audio=[audio], return_tensors="pt", padding=True)
        else:
            inputs = self.processor.apply_transcription_request(audio=audio, prompt=prompt, language=language_name)
        inputs = inputs.to(self.device, self.dtype)
        with self.torch.inference_mode():
            output = self.model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=self.max_new_tokens,
                return_dict_in_generate=True,
                output_scores=True,
                **({"eos_token_id": [151643, 151645]} if self.backend == "official" else {}),
            )
        tokens = output.sequences[:, inputs["input_ids"].shape[1] :]
        eos = [151643, 151645] if self.backend == "official" else self.model.generation_config.eos_token_id
        eos = eos if isinstance(eos, list) else [eos]
        if self.backend == "official":
            from qwen_asr.inference.utils import parse_asr_output

            raw = self.processor.batch_decode(tokens, skip_special_tokens=False, clean_up_tokenization_spaces=False)[0]
            cleaned = self.processor.batch_decode(tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
            language, text = parse_asr_output(cleaned, user_language=language_name)
            parsed = {"language": language, "transcription": text}
        else:
            parsed = self.processor.decode(tokens, return_format="parsed")[0]
            raw = self.processor.decode(tokens)[0]
        logprobs = [
            float(self.torch.log_softmax(score[0].float(), dim=-1)[int(token)])
            for token, score in zip(tokens[0], output.scores, strict=True)
        ]
        if tokens.shape[1] >= self.max_new_tokens and int(tokens[0, -1]) not in eos:
            raise TruncatedASR({
                "start_sample": start_sample, "end_sample": end_sample,
                "output": raw, "token_ids": tokens[0].tolist(), "token_logprobs": logprobs,
                "context": prompt, "status": "truncated_not_publishable",
            })
        return ASRResult(
            engine="qwen_asr",
            model=self.manifest["repo"],
            model_version=self.manifest["revision"],
            runtime="transformers " + importlib.metadata.version("transformers"),
            precision=self.precision,
            device=self.device,
            text=parsed["transcription"],
            start_sample=start_sample,
            end_sample=end_sample,
            language=None if language_hint else parsed.get("language") or None,
            language_scope="forced_hint_not_language_detection" if language_hint else "dominant_window_tag_not_word_labels",
            latency_ms=(time.monotonic() - started) * 1000,
            raw={
                "output": raw,
                "token_ids": tokens[0].tolist(),
                "token_logprobs": logprobs,
                "score_status": "uncalibrated model token likelihood, not word accuracy",
                "context": prompt,
                "backend": self.backend,
                "diagnostic_language_hint": language_hint,
            },
            unavailable=[
                "word_timestamps",
                "span_language_labels",
                "calibrated_confidence",
                "native_streaming",
            ],
        )
