from typing import Literal

from pydantic import BaseModel


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
