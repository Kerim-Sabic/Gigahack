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


def locate_literal_fields(candidate, segments):
    """Locate proposed literals only inside already cited text spans.

    This supplies traceable offsets, not semantic verification. Ambiguous/missing
    occurrences remain unsupported; a reviewer must still confirm responsibility.
    """
    for field in ("owner", "due", "condition", "value"):
        value = candidate.raw_due if field == "due" else getattr(candidate, field)
        if not value or any(r.field == field for r in candidate.evidence):
            continue
        matches = {}
        for ref in candidate.evidence:
            source = segments.get(ref.segment_id)
            if (
                ref.field != "text"
                or value not in ref.quote
                or not source
                or source["revision"] != ref.revision
            ):
                continue
            if source["text"].count(ref.quote) == 1 and source["text"].count(value) == 1:
                matches[ref.segment_id] = ref
        if len(matches) == 1:
            ref = next(iter(matches.values()))
            candidate.evidence.append(
                Citation(segment_id=ref.segment_id, revision=ref.revision, field=field, quote=value)
            )
            candidate.uncertainties.append(
                f"{field}: literal span located in cited text; reviewer must confirm interpretation"
            )
    return candidate


def withhold_uncited_fields(candidate):
    """Retain reviewable text while refusing optional values without field support.

    This does not repair quotes or invent citations. validate_evidence must still run.
    """
    for field in ("owner", "due", "condition", "value"):
        value = candidate.raw_due if field == "due" else getattr(candidate, field)
        refs = [e for e in candidate.evidence if e.field == field]
        supported = bool(refs)
        if value is not None:
            supported = any(value.casefold() in e.quote.casefold() for e in refs)
        if value is not None and not supported:
            setattr(candidate, field, None)
            if field == "due":
                candidate.raw_due = None
            candidate.uncertainties.append(f"{field} withheld: field-specific source support missing")
    return candidate


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
    if "text" not in fields:
        raise ValueError("missing_text_evidence")
    for field in ("owner", "due", "condition", "value"):
        if getattr(candidate, field) is not None and field not in fields:
            raise ValueError(f"missing_{field}_evidence")
    if candidate.raw_due is not None and "due" not in fields:
        raise ValueError("missing_raw_due_evidence")
    for field in ("owner", "value", "condition", "due"):
        value = candidate.raw_due if field == "due" else getattr(candidate, field)
        if value is not None and not any(
            value.casefold() in e.quote.casefold() for e in candidate.evidence if e.field == field
        ):
            raise ValueError(f"unsupported_{field}_value")
    return refs


def event_key(event):
    # Citation order and repeated citations are incidental to overlapping windows.
    # Different source revisions and field amendments must remain distinct.
    content = {
        k: event.get(k)
        for k in ("subject", "category", "kind", "text", "owner", "due", "raw_due", "condition", "value")
    }
    content["changed_fields"] = sorted(set(event.get("changed_fields", [])))
    content["evidence"] = sorted(
        {json.dumps(ref, sort_keys=True, ensure_ascii=False) for ref in event["evidence"]}
    )
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
        item = subjects.setdefault(
            subject,
            {
                "subject": subject,
                "category": e["category"],
                "status": "proposed",
                "text": e["text"],
                "owner": None,
                "due": None,
                "condition": None,
                "value": None,
                "history": [],
                "pending": [],
                "evidence": [],
            },
        )
        item["history"].append({**e, "event_id": row["id"]})
        kind = e["kind"]
        if e.get("human_amendment"):
            item["category"] = e["category"]
        if kind == "inform" and item["status"] in ("confirmed", "cancelled", "rejected"):
            continue
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
            updated_fields = set(e["changed_fields"])
            for f in e["changed_fields"]:
                item[f] = e[f]
        else:
            updated_fields = set()
            for f in ("text", "owner", "due", "condition", "value"):
                if e[f] is not None or f == "text":
                    item[f] = e[f]
                    updated_fields.add(f)
        item["category"] = e["category"]
        # A partial amendment must keep the source of every unchanged projected field.
        # In particular, changing an owner cannot erase the approved date's citation.
        updated_fields.add("kind")
        item["evidence"] = [r for r in item["evidence"] if r["field"] not in updated_fields] + [
            r for r in e["evidence"] if r["field"] in updated_fields
        ]
        item["uncertainties"] = e["uncertainties"]
        if kind in ("confirm", "reopen", "amend"):
            item["status"] = "confirmed"
        elif kind == "inform":
            item["status"] = "information"
    return list(subjects.values())
