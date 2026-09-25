"""Evidence validation and source-ordered, field-preserving event reduction."""
import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Citation(Strict):
    segment_id: str
    revision: int
    field: Literal["text", "owner", "due", "condition", "value", "kind"]
    quote: str = Field(min_length=1, max_length=2000)


class Candidate(Strict):
    subject: str = Field(min_length=1, max_length=160)
    category: Literal["action", "decision", "information"]
    kind: Literal["propose", "confirm", "amend", "reject", "cancel", "reopen", "inform"]
    text: str = Field(min_length=1, max_length=2000)
    owner: str | None = None
    due: str | None = None
    raw_due: str | None = None
    condition: str | None = None
    value: str | None = None
    changed_fields: list[Literal["text", "owner", "due", "condition", "value"]] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    evidence: list[Citation] = Field(min_length=1, max_length=20)


class Extraction(Strict):
    events: list[Candidate] = Field(max_length=12)


def validate_evidence(candidate, segments):
    refs = []
    for e in candidate.evidence:
        s = segments.get(e.segment_id)
        if not s or s["revision"] != e.revision:
            raise ValueError("source_revision_mismatch")
        text = s["text"]
        start = text.find(e.quote)
        if start < 0 or text.find(e.quote, start + 1) >= 0:
            raise ValueError("quote_missing_or_ambiguous")
        refs.append({**e.model_dump(), "start": start, "end": start + len(e.quote)})
    fields = {e.field for e in candidate.evidence}
    for field in ("owner", "due", "condition", "value"):
        if getattr(candidate, field) is not None and field not in fields:
            raise ValueError(f"missing_{field}_evidence")
    return refs


def event_key(event):
    content = {k: event[k] for k in ("subject", "category", "kind", "text", "owner", "due", "condition", "value", "evidence")}
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def reduce_events(events):
    """Only caller-authorized accepted events enter here. Arrival order has no meaning."""
    subjects = {}
    seen = set()
    for row in sorted(events, key=lambda r: (r["source_order"], r["id"])):
        e = json.loads(row["body"]) if isinstance(row["body"], str) else row["body"]
        key = event_key(e)
        if key in seen:
            continue
        seen.add(key)
        subject = e["subject"]
        item = subjects.setdefault(subject, {"subject": subject, "category": e["category"],
            "status": "proposed", "text": e["text"], "owner": None, "due": None,
            "condition": None, "value": None, "history": [], "pending": [], "evidence": []})
        item["history"].append({**e, "event_id": row["id"]})
        kind = e["kind"]
        if kind == "propose":
            item["pending"].append(e)
            if item["status"] != "proposed":
                continue
        if kind in ("confirm", "amend") and item["status"] == "cancelled":
            item["pending"].append(e)
            continue
        if kind == "reject":
            if item["status"] != "confirmed":
                item["status"] = "rejected"
            continue
        if kind == "cancel":
            item["status"] = "cancelled"
            continue
        if kind == "amend":
            for f in e["changed_fields"]:
                item[f] = e[f]
        else:
            for f in ("text", "owner", "due", "condition", "value"):
                if e[f] is not None or f == "text":
                    item[f] = e[f]
        item["evidence"] = e["evidence"]
        item["uncertainties"] = e["uncertainties"]
        if kind in ("confirm", "reopen"):
            item["status"] = "confirmed"
        elif kind == "inform":
            item["status"] = "information"
    return list(subjects.values())
