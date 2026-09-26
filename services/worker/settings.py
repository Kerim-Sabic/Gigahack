"""Validated developer controls, serialized into jobs instead of mutable globals."""

import tomllib
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from services.api.config import ROOT


class FrozenSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LocalModelSettings(FrozenSettings):
    model_directory: str

    @field_validator("model_directory")
    @classmethod
    def model_name(cls, value):
        if not value or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in value):
            raise ValueError("model_directory_must_be_a_prepared_manifest_name")
        return value


class LLMSettings(LocalModelSettings):
    model_file: str
    context_tokens: int = Field(ge=2048, le=131072)
    source_window_tokens: int = Field(ge=128)
    reconciliation_tokens: int = Field(ge=128)
    extraction_tokens: int = Field(ge=128)
    classification_tokens: int = Field(ge=32)
    category_tokens: int = Field(ge=16)
    field_tokens: int = Field(ge=64)
    reasoning_tokens: int = Field(ge=0, le=8192)
    reasoning_overhead_tokens: int = Field(ge=0, le=256)
    temperature: float = Field(ge=0, le=2)
    batch_size: int = Field(ge=1, le=2048)
    micro_batch_size: int = Field(ge=1, le=2048)
    gpu_layers: int = Field(ge=-1, le=1000)
    request_timeout_seconds: int = Field(ge=10, le=3600)
    startup_timeout_seconds: int = Field(ge=10, le=1800)
    split_depth: int = Field(ge=1, le=20)

    @field_validator("model_file")
    @classmethod
    def model_filename(cls, value):
        if not value.endswith(".gguf") or any(c in value for c in ("/", "\\", ":")) or value.startswith("."):
            raise ValueError("model_file_must_be_a_local_gguf_basename")
        return value

    @model_validator(mode="after")
    def budgets(self):
        if self.micro_batch_size > self.batch_size:
            raise ValueError("micro_batch_exceeds_batch")
        reasoning = self.reasoning_tokens + self.reasoning_overhead_tokens if self.reasoning_tokens else 0
        if self.source_window_tokens + self.extraction_tokens >= self.context_tokens:
            raise ValueError("source_and_output_exceed_context")
        if self.reconciliation_tokens + max(self.classification_tokens, self.category_tokens, self.field_tokens) + reasoning >= self.context_tokens:
            raise ValueError("interpretation_and_output_exceed_context")
        return self


class ASRSettings(LocalModelSettings):
    checkpoint_seconds: int = Field(ge=30, le=600)
    overlap_seconds: int = Field(ge=1, le=10)
    beam_size: int = Field(ge=1, le=10)
    decode_window_seconds: int = Field(ge=5, le=30)
    retry_window_seconds: int = Field(ge=5, le=30)
    condition_on_previous_text: bool
    multilingual: bool
    vad_filter: bool
    gpu_compute_type: Literal["int8_float16", "float16", "float32", "int8"]
    cpu_compute_type: Literal["int8", "float32"]


class OptionalSettings(FrozenSettings):
    runtime_prefix: str = Field(default="", max_length=4096)
    parakeet_audio_fraction: float = Field(gt=0, le=1)
    parakeet_batch_size: int = Field(ge=1, le=8)
    diarization_batch_size: int = Field(ge=1, le=64)
    recovery_window_seconds: int = Field(default=20, ge=5, le=25)
    recovery_retry_seconds: int = Field(default=10, ge=5, le=20)
    recovery_padding_seconds: int = Field(default=2, ge=0, le=5)

    @model_validator(mode="after")
    def recovery_windows(self):
        if self.recovery_retry_seconds >= self.recovery_window_seconds:
            raise ValueError("recovery_retry_must_be_shorter")
        if self.recovery_window_seconds + 2 * self.recovery_padding_seconds > 25:
            raise ValueError("recovery_context_exceeds_25_seconds")
        return self

    @field_validator("runtime_prefix")
    @classmethod
    def local_runtime(cls, value):
        if value and ("\0" in value or not value.startswith("/")):
            raise ValueError("optional_runtime_requires_an_absolute_linux_path")
        return value


class WorkerSettings(FrozenSettings):
    no_activity_timeout_seconds: int = Field(ge=60, le=86400)


class InferenceSettings(FrozenSettings):
    schema_version: Literal[1]
    llm: LLMSettings
    asr: ASRSettings
    optional: OptionalSettings
    worker: WorkerSettings


def load_settings(path: Path | None = None):
    with (path or ROOT / "config/inference.toml").open("rb") as source:
        values = tomllib.load(source)
    if os.environ.get("MOM_OPTIONAL_RUNTIME"):
        values["optional"]["runtime_prefix"] = os.environ["MOM_OPTIONAL_RUNTIME"]
    return InferenceSettings.model_validate(values)


def settings_for(spec):
    frozen = spec.get("config", {}).get("inference")
    return InferenceSettings.model_validate(frozen) if frozen is not None else load_settings()
