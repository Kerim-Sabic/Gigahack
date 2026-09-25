import pytest

from services.api.domain import Candidate, reduce_events, validate_evidence, withhold_uncited_fields


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
