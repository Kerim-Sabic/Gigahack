"""Source-clock contracts; unavailable timestamps or confidence are never fabricated."""

from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class LanguageSpan(Strict):
    language: str | None = None
    start_char: int = Field(ge=0)
    end_char: int = Field(gt=0)
    basis: Literal["model", "human", "script_candidate"]
    start_sample: int | None = Field(default=None, ge=0)
    end_sample: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def bounds(self):
        if self.end_char <= self.start_char:
            raise ValueError("empty_language_span")
        if (self.start_sample is None) != (self.end_sample is None):
            raise ValueError("incomplete_language_timing")
        if self.start_sample is not None and self.end_sample <= self.start_sample:
            raise ValueError("invalid_language_timing")
        return self


class Word(Strict):
    text: str = Field(min_length=1)
    start_sample: int = Field(ge=0)
    end_sample: int = Field(gt=0)
    timing_source: str

    @model_validator(mode="after")
    def bounds(self):
        if self.end_sample <= self.start_sample:
            raise ValueError("invalid_word_timing")
        return self


class ASRResult(Strict):
    engine: str
    model: str
    model_version: str
    runtime: str
    precision: str
    device: str
    text: str
    start_sample: int = Field(ge=0)
    end_sample: int = Field(gt=0)
    sample_rate: Literal[16000] = 16000
    words: list[Word] | None = None
    language: str | None = None
    language_scope: str = "unavailable"
    language_spans: list[LanguageSpan] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    confidence_basis: Literal["unavailable", "validated_calibration"] = "unavailable"
    latency_ms: float = Field(ge=0)
    raw: dict = Field(default_factory=dict)
    unavailable: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def evidence_bounds(self):
        if self.end_sample <= self.start_sample:
            raise ValueError("invalid_source_window")
        if (self.confidence is None) != (self.confidence_basis == "unavailable"):
            raise ValueError("confidence_requires_measured_calibration")
        last = 0
        for span in self.language_spans:
            if span.start_char < last or span.end_char > len(self.text):
                raise ValueError("invalid_language_span_coverage")
            if (
                span.start_sample is not None
                and not self.start_sample <= span.start_sample < span.end_sample <= self.end_sample
            ):
                raise ValueError("language_timing_outside_source")
            last = span.end_char
        for word in self.words or []:
            if not self.start_sample <= word.start_sample < word.end_sample <= self.end_sample:
                raise ValueError("word_timing_outside_source")
        return self


class ASREngine(ABC):
    @abstractmethod
    def transcribe(self, audio_path, start_sample, end_sample, *, terms=(), language_hint=None) -> ASRResult:
        raise NotImplementedError

    @abstractmethod
    def supports_language(self, language):
        raise NotImplementedError

    def supports_streaming(self):
        return False

    def transcribe_stream(self, chunks):
        raise NotImplementedError("This adapter has no qualified streaming implementation")

    def get_word_timestamps(self, result):
        return result.words

    def get_confidence(self, result):
        return result.confidence

    @abstractmethod
    def health_check(self):
        raise NotImplementedError
