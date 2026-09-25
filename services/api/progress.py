"""Content-free, best-effort progress artifacts; never authoritative job success."""

import json
import math
import os
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ProgressView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stage: Literal["whisper", "extract", "parakeet", "diarize"]
    phase: Literal["loading_model", "transcribing", "extracting", "checking", "diarizing", "stage_complete"]
    completed: float = Field(ge=0, allow_inf_nan=False)
    total: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    unit: Literal["seconds", "segments", "items", "clips"]
    elapsed_seconds: float = Field(ge=0, allow_inf_nan=False)
    eta_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    eta_scope: Literal["current_phase"] = "current_phase"
    updated_at: float = Field(ge=0, allow_inf_nan=False)


class ProgressReporter:
    def __init__(self, directory, stage, clock=time.monotonic, wall_clock=time.time):
        self.path = Path(directory) / "progress.json"
        self.stage, self.clock, self.wall_clock = stage, clock, wall_clock
        self.begin("loading_model")

    def begin(self, phase, total=None, unit="items", initial_completed=0):
        self.phase, self.total, self.unit = phase, total, unit
        self.started = self.clock()
        self.completed, self.observations = float(initial_completed), 0
        self.initial_completed = self.completed
        self.last_written = float("-inf")
        self.advance(self.completed, force=True)

    def advance(self, completed, force=False):
        if not math.isfinite(completed) or completed < self.completed:
            raise ValueError("invalid_progress_observation")
        if self.total is not None and completed > self.total:
            completed = self.total
        self.observations += completed > self.completed
        self.completed = completed
        now = self.clock()
        elapsed = max(0, now - self.started)
        if not force and now - self.last_written < 0.5 and completed != self.total:
            return
        self.last_written = now
        eta = None
        observed_work = completed - self.initial_completed
        if self.total and self.observations >= 2 and elapsed >= 3 and observed_work > 0:
            eta = elapsed / observed_work * max(0, self.total - completed)
        value = ProgressView(stage=self.stage, phase=self.phase, completed=completed, total=self.total,
                             unit=self.unit, elapsed_seconds=elapsed, eta_seconds=eta, updated_at=self.wall_clock())
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".json.partial")
            temporary.write_text(value.model_dump_json(), encoding="utf-8")
            os.replace(temporary, self.path)
        except OSError:
            pass  # Progress display failure cannot destroy successful analysis work.


def read_progress(directory, job):
    if job["state"] == "queued":
        return None
    path = Path(directory) / "jobs" / job["id"] / "progress.json"
    try:
        if path.stat().st_size > 16384:
            return None
        value = ProgressView.model_validate(json.loads(path.read_text(encoding="utf-8")))
        if value.stage != job["stage"] or (value.total and value.completed > value.total):
            return None
        return value.model_dump()
    except (OSError, ValueError, ValidationError):
        return None
