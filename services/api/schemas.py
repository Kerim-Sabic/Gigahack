from typing import Literal

from pydantic import BaseModel, Field
from .progress import ProgressView


class AccountSummary(BaseModel):
    id: str
    name: str
    role: Literal["admin", "secretary", "viewer"]
    language: Literal["en", "ro", "ru"] = "en"


class AccountView(AccountSummary):
    csrf: str


class MeetingView(BaseModel):
    id: str
    title: str
    date: str
    timezone: str
    language: Literal["en", "ro", "ru"]
    classification: Literal["Medical", "Executive", "Administrative"]
    revision: int
    status: str
    created: float
    time: str = ""
    notes: str = ""


class ParticipantView(BaseModel):
    id: str
    meeting_id: str
    name: str


class AssetView(BaseModel):
    id: str
    meeting_id: str
    hash: str
    sample_rate: int
    samples: int
    channels: int
    original: str


class JobView(BaseModel):
    id: str
    meeting_id: str
    asset_id: str
    state: str
    stage: str
    error: str | None
    attempt: int
    cancel: int
    created: float
    progress: ProgressView | None = None
    transcript_only: bool = False


class RecordingView(BaseModel):
    id: str
    meeting_id: str
    rate: int
    state: str
    gaps: str
    acknowledged_chunks: int
    acknowledged_samples: int
    last_sequence: int | None


class MeetingDetail(MeetingView):
    participants: list[ParticipantView]
    assets: list[AssetView]
    jobs: list[JobView]
    recordings: list[RecordingView]
    transcript_pending_assets: list[str] = Field(default_factory=list)


class SegmentView(BaseModel):
    id: str
    meeting_id: str
    asset_id: str
    revision: int
    start: int
    end: int
    text: str
    raw: str
    speaker: str | None
    alternatives: str
    words: str


class RecoveryHypothesis(BaseModel):
    engine: Literal["parakeet"]
    text: str
    attempt: Literal["initial", "short_retry"]
    source_start: int = Field(ge=0)
    source_end: int = Field(gt=0)
    primary_start: int = Field(ge=0)
    primary_end: int = Field(gt=0)
    timestamps: dict
    review: Literal["unreviewed"]


class AudioCheckView(BaseModel):
    kind: Literal["speech_without_transcript", "empty_second_recognizer"]
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    hypotheses: list[RecoveryHypothesis] = Field(default_factory=list)
    inserted_segment_id: str | None = None


class AudioChecksPage(BaseModel):
    asset_id: str
    total: int = Field(ge=0)
    items: list[AudioCheckView]
    scope: str
