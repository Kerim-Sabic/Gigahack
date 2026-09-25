import pytest

from services.api.domain import Candidate, reduce_events, validate_evidence, withhold_uncited_fields
from services.api.domain import locate_literal_fields
from services.api.domain import event_key


def test_overlap_identity_is_canonical_but_preserves_amendments():
    from copy import deepcopy

    first = event("confirm", 1, raw_due="tomorrow")
    a = {"segment_id": "s1", "revision": 1, "field": "text", "quote": "Send it"}
    b = {"segment_id": "s2", "revision": 1, "field": "due", "quote": "tomorrow"}
    first["body"]["evidence"] = [a, b]
    repeated = deepcopy(first)
    repeated["id"] = "overlap"
    repeated["body"]["evidence"] = deepcopy([b, a, b])
    assert event_key(first["body"]) == event_key(repeated["body"])
    assert len(reduce_events([first, repeated])[0]["history"]) == 1
    for changed in ({"raw_due": "next day"}, {"changed_fields": ["due"]}):
        assert event_key(first["body"]) != event_key({**first["body"], **changed})
    repeated["body"]["evidence"][0]["revision"] = 2
    assert event_key(first["body"]) != event_key(repeated["body"])


def event(kind, order, **kwargs):
    return {
        "id": str(order),
        "source_order": order,
        "body": {
            "subject": "maintenance",
            "category": "action",
            "kind": kind,
            "text": "Maintenance",
            "owner": None,
            "due": None,
            "condition": None,
            "value": None,
            "changed_fields": [],
            "uncertainties": [],
            "evidence": [],
            **kwargs,
        },
    }


def test_late_ingestion_replays_source_and_preserves_other_fields():
    events = [
        event("amend", 2, owner="Elena", changed_fields=["owner"]),
        event("confirm", 1, owner="Andrei", due="2026-09-30"),
    ]
    item = reduce_events(events)[0]
    assert (item["owner"], item["due"]) == ("Elena", "2026-09-30")


def test_proposal_does_not_replace_active_and_cancel_requires_reopen():
    events = [event("confirm", 1, due="2026-09-30"), event("propose", 2, due="2026-10-02")]
    assert reduce_events(events)[0]["due"] == "2026-09-30"
    events += [event("cancel", 3), event("confirm", 4)]
    assert reduce_events(events)[0]["status"] == "cancelled"
    events += [event("reopen", 5, owner="Elena")]
    assert reduce_events(events)[0]["status"] == "confirmed"


def test_rejected_is_not_active_and_condition_survives():
    assert reduce_events([event("propose", 1), event("reject", 2)])[0]["status"] == "rejected"
    item = reduce_events(
        [
            event("confirm", 1, condition="If procurement approves"),
            event("amend", 2, owner="Elena", changed_fields=["owner"]),
        ]
    )[0]
    assert item["condition"] == "If procurement approves"


def test_discussion_cannot_reactivate_cancelled_task():
    item = reduce_events([event("cancel", 1), event("inform", 2, text="We are only discussing it")])[0]
    assert item["status"] == "cancelled"


def test_evidence_unicode_and_ambiguity():
    body = event("confirm", 1)["body"]
    body["evidence"] = [{"segment_id": "s", "revision": 1, "field": "text", "quote": "ședința"}]
    candidate = Candidate.model_validate(body)
    assert validate_evidence(candidate, {"s": {"revision": 1, "text": "O ședința"}})[0]["start"] == 2
    with pytest.raises(ValueError):
        validate_evidence(candidate, {"s": {"revision": 1, "text": "ședința ședința"}})
    with pytest.raises(ValueError):
        validate_evidence(candidate, {"s": {"revision": 2, "text": "ședința"}})


@pytest.mark.parametrize(("field", "value"), [("condition", "If everyone agrees"), ("raw_due", "tomorrow")])
def test_field_quote_presence_does_not_support_an_invented_value(field, value):
    body = event("confirm", 1)["body"]
    body[field] = value
    evidence_field = "due" if field == "raw_due" else field
    body["evidence"] = [
        {"segment_id": "s", "revision": 1, "field": f, "quote": "Elena sends the report"}
        for f in ("text", evidence_field)
    ]
    candidate = Candidate.model_validate(body)
    with pytest.raises(ValueError, match="unsupported_"):
        validate_evidence(candidate, {"s": {"revision": 1, "text": "Elena sends the report"}})
    withhold_uncited_fields(candidate)
    assert getattr(candidate, field) is None


def test_literal_linker_uses_cited_text_and_withholds_ambiguous_mentions():
    body = event("confirm", 1, owner="Elena")["body"]
    body["evidence"] = [
        {"segment_id": "s", "revision": 1, "field": "text", "quote": "Elena sends the report"}
    ]
    sources = {"s": {"revision": 1, "text": "Elena sends the report"}}
    candidate = locate_literal_fields(Candidate.model_validate(body), sources)
    assert any(r.field == "owner" and r.quote == "Elena" for r in candidate.evidence)
    validate_evidence(candidate, sources)
    assert candidate.uncertainties
    sources["s"]["text"] += "; ask Elena later"
    candidate = locate_literal_fields(Candidate.model_validate(body), sources)
    assert not any(r.field == "owner" for r in candidate.evidence)
    withhold_uncited_fields(candidate)
    assert candidate.owner is None


def test_partial_amendment_keeps_unchanged_field_citations():
    date_ref = {"field": "due", "segment_id": "first", "quote": "30 September"}
    old_owner = {"field": "owner", "segment_id": "first", "quote": "Andrei"}
    new_owner = {"field": "owner", "segment_id": "later", "quote": "Elena"}
    item = reduce_events(
        [
            event("confirm", 1, owner="Andrei", due="2026-09-30", evidence=[date_ref, old_owner]),
            event("amend", 2, owner="Elena", changed_fields=["owner"], evidence=[new_owner]),
        ]
    )[0]
    assert item["evidence"] == [date_ref, new_owner]
    assert item["due"] == "2026-09-30"


def test_confirmed_task_updates_category_of_earlier_discussion():
    item = reduce_events([event("inform", 1, category="information"), event("confirm", 2)])[0]
    assert item["category"] == "action"


def test_uncited_optional_field_is_withheld_but_invalid_source_is_rejected():
    body = event("confirm", 1, owner="Elena", value="50 mg")["body"]
    body["evidence"] = [{"segment_id": "s", "revision": 1, "field": "text", "quote": "Send report"}]
    candidate = withhold_uncited_fields(Candidate.model_validate(body))
    assert candidate.owner is None and candidate.value is None
    assert len(candidate.uncertainties) == 2
    validate_evidence(candidate, {"s": {"revision": 1, "text": "Send report"}})
    with pytest.raises(ValueError, match="quote_missing"):
        validate_evidence(candidate, {"s": {"revision": 1, "text": "Other source"}})
