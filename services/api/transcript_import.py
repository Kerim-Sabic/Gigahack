"""Import supplied speaker/timestamp text without claiming ASR or human verification."""
import hashlib
import re
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from pydantic import Field

from .audio import atomic_write
from .db import audit, canonical, transaction, uid
from .domain import Candidate, Strict, validate_evidence
from .storage import require_space
from .transcript_state import changed

router = APIRouter(prefix="/api/v1")
HEADER = re.compile(r"^Speaker ([1-9][0-9]*)\s*\r?\n(\d{1,3}):([0-5][0-9])\s*\r?\n", re.MULTILINE)
LABELS = {"Italian", "Macedonian", "Serbian", "Japanese", "Romanian", "Russian", "English"}


def parse_transcript(source, samples, rate):
    matches = list(HEADER.finditer(source))
    if not matches or source[:matches[0].start()].strip("\ufeff \r\n\t"):
        raise ValueError("expected_speaker_timestamp_transcript")
    rows = []
    for index, match in enumerate(matches):
        start = (int(match[2]) * 60 + int(match[3])) * rate
        raw = source[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(source)].strip()
        text, labels = raw, []
        first, separator, rest = raw.partition("\n")
        if separator and first.strip() in LABELS:
            labels = [first.strip()]
            text = rest.strip()
        if not text or len(text) > 10000 or not 0 <= start < samples:
            raise ValueError("invalid_transcript_text_or_timestamp")
        rows.append({"start": start, "speaker": "Speaker " + match[1], "text": text,
                     "source_index": index, "source_text": raw, "supplied_language_labels": labels})
    starts = sorted({r["start"] for r in rows} | {samples})
    ends = dict(zip(starts, starts[1:]))
    for row in rows:
        row["end"] = ends[row["start"]]
    # Equal anchors remain overlapping; source order is retained in provenance.
    return sorted(rows, key=lambda r: (r["start"], r["source_index"]))


class ImportTranscript(Strict):
    asset_id: str
    revision: int = Field(ge=1)
    source: str = Field(min_length=1, max_length=2_000_000)
    filename: str = Field(min_length=1, max_length=200)


def authenticated(request: Request):
    from .main import user
    return user(request)


@router.post("/meetings/{ident}/transcript-imports")
def import_transcript(ident: str, body: ImportTranscript, u=Depends(authenticated)):
    from .main import access, fail
    content = body.source.encode("utf-8")
    digest = hashlib.sha256(content).hexdigest()
    with transaction() as c:
        meeting = access(c, ident, u, True)
        asset = c.execute("SELECT * FROM assets WHERE id=? AND meeting_id=?", (body.asset_id, ident)).fetchone()
        if not asset:
            fail("asset_not_found", 404)
        existing = c.execute("SELECT raw FROM segments WHERE asset_id=?", (body.asset_id,)).fetchall()
        if existing:
            import json
            if all(json.loads(r[0]).get("source_sha256") == digest for r in existing):
                return {"segments": len(existing), "sha256": digest, "already_imported": True}
            fail("transcript_already_exists", 409)
        if meeting["revision"] != body.revision:
            fail("revision_conflict", 409)
        if c.execute("SELECT 1 FROM jobs WHERE meeting_id=? AND state IN ('queued','running')", (ident,)).fetchone():
            fail("processing_incomplete", 409)
        try:
            rows = parse_transcript(body.source, asset["samples"], asset["sample_rate"])
        except ValueError as exc:
            fail(str(exc), 422)
        folder = Path(asset["path"]).parent
        require_space(folder, len(content))
        atomic_write(folder / ("transcript-" + digest + ".txt"), content)
        for row in rows:
            raw = {"origin": "user_supplied_transcript", "verified_against_audio": False,
                   "source_sha256": digest, "filename": body.filename, "actor": u["id"],
                   "imported_at": time.time(), "timing": "supplied coarse anchors; end inferred from next distinct anchor",
                   **{key: row[key] for key in ("source_index", "source_text", "supplied_language_labels")}}
            c.execute("INSERT INTO segments(id,meeting_id,asset_id,revision,start,end,text,raw,speaker) VALUES(?,?,?,1,?,?,?,?,?)",
                      (uid(), ident, body.asset_id, row["start"], row["end"], row["text"], canonical(raw), row["speaker"]))
        changed(c, ident, body.asset_id)
        audit(c, ident, u["id"], "transcript_imported", {"asset": body.asset_id, "sha256": digest, "segments": len(rows)})
        return {"segments": len(rows), "sha256": digest, "already_imported": False}


class SourceDraft(Strict):
    revision: int = Field(ge=1)
    asset_id: str
    source_versions: dict[str, int]
    events: list[Candidate] = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=3, max_length=1000)


@router.post("/meetings/{ident}/transcript-draft")
def source_draft(ident: str, body: SourceDraft, u=Depends(authenticated)):
    """Explicit source-based authoring is an alternative to model extraction, not approval."""
    from .main import access, fail
    with transaction() as c:
        meeting = access(c, ident, u, True)
        if meeting["revision"] != body.revision:
            fail("revision_conflict", 409)
        if c.execute("SELECT 1 FROM jobs WHERE meeting_id=? AND state IN ('queued','running')", (ident,)).fetchone():
            fail("processing_incomplete", 409)
        segments = {r["id"]: dict(r) for r in c.execute(
            "SELECT * FROM segments WHERE meeting_id=? AND asset_id=?", (ident, body.asset_id))}
        if not segments or body.source_versions != {key: row["revision"] for key, row in segments.items()}:
            fail("source_revision_mismatch", 409)
        if c.execute("SELECT 1 FROM candidates WHERE meeting_id=?", (ident,)).fetchone():
            fail("draft_already_exists", 409)
        validated = []
        for event in body.events:
            try:
                refs = validate_evidence(event, segments)
            except ValueError as exc:
                fail(str(exc), 422)
            validated.append((event, refs))
        for event, refs in validated:
            candidate = uid()
            order = min(segments[r["segment_id"]]["start"] for r in refs)
            c.execute("INSERT INTO candidates(id,meeting_id,subject,body,review,source_order,actor,created) VALUES(?,?,?,?,'unreviewed',?,?,?)",
                      (candidate, ident, event.subject, canonical(event.model_dump()), order, u["id"], time.time()))
            for ref in refs:
                c.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?)",
                          (uid(), ident, candidate, ref["segment_id"], ref["revision"], ref["field"], ref["quote"], ref["start"], ref["end"]))
        c.execute("DELETE FROM transcript_analysis_state WHERE meeting_id=? AND asset_id=?", (ident, body.asset_id))
        c.execute("UPDATE meetings SET revision=revision+1,status='awaiting_review' WHERE id=?", (ident,))
        audit(c, ident, u["id"], "source_based_draft_authored", {"asset": body.asset_id,
              "reason": body.reason, "source_versions": body.source_versions, "items": len(validated),
              "origin": "explicit source-based authoring; not model extraction or audio verification"})
        return {"items": len(validated), "revision": meeting["revision"] + 1}
