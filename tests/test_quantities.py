from copy import deepcopy

import pytest

from services.api.quantities import enrich_quantity, parts


def candidate(text, value, subject="room capacity"):
    ref = {"segment_id": "s", "revision": 1, "field": "text", "quote": text}
    return {"subject": subject, "value": value, "evidence": [ref], "uncertainties": []}


@pytest.mark.parametrize(
    ("text", "value", "unit", "raw"),
    [
        ("No, 16 chairs for Room C, agreed.", "16", "chairs", "16 chairs"),
        ("The budget is 950 lei.", "950", "lei", "950 lei"),
        ("Обсуждаем 5 мг.", "5", "мг", "5 мг"),
        ("Volumul este 0,5 ml.", "0,5", "ml", "0,5 ml"),
        ("Budget €1200 approved.", "1200", "€", "€1200"),
        ("Corecție: 34 de paturi pentru secția C.", "34", "paturi", "34 de paturi"),
    ],
)
def test_quantity_uses_literal_amount_unit_and_scope(text, value, unit, raw):
    event = candidate(text, value)
    enrich_quantity(event, {"s": {"text": text, "revision": 1}})
    assert event["value"] == raw
    assert event["quantity"]["amount"] == value
    assert event["quantity"]["unit"] == unit
    assert event["quantity"]["scope"] == "room capacity"
    assert event["quantity"]["evidence"][0]["quote"] == raw
    assert raw in text


def test_same_number_with_noninterchangeable_units_is_not_arbitrarily_selected():
    text = "The reading could mean 5 mg or 5 ml."
    event = candidate(text, "5")
    enrich_quantity(event, {"s": {"text": text, "revision": 1}})
    assert "quantity" not in event
    assert "ambiguous" in event["uncertainties"][0]


def test_no_inherited_unit_from_uncited_other_subject():
    event = candidate("Set the count to 9.", "9", "Room S")
    source = {
        "s": {"text": "Set the count to 9.", "revision": 1},
        "other": {"text": "Room R has 9 pumps.", "revision": 1},
    }
    enrich_quantity(event, source)
    assert event["quantity"]["unit"] is None
    assert event["quantity"]["scope"] == "Room S"
    assert event["quantity"]["uncertainties"]


def test_quantity_does_not_change_speech_act_or_make_a_clinical_action():
    text = "The protocol discussion mentions 5 mg."
    event = {**candidate(text, "5"), "category": "information", "kind": "inform"}
    before = deepcopy(event)
    enrich_quantity(event, {"s": {"text": text, "revision": 1}})
    assert (event["kind"], event["category"]) == (before["kind"], before["category"])
    assert parts("5 mg") != parts("5 ml")


def test_unresolved_numbers_are_not_reconstructed():
    text = "It could be 0.5 mg or 5 mg."
    event = candidate(text, None)
    enrich_quantity(event, {"s": {"text": text, "revision": 1}})
    assert "quantity" not in event and event["value"] is None


def test_unknown_unit_alternative_cannot_be_discarded():
    text = "The reading is 5 mg or 5 widgets."
    event = candidate(text, "5")
    enrich_quantity(event, {"s": {"text": text, "revision": 1}})
    assert "quantity" not in event
    assert "ambiguous" in event["uncertainties"][0]


def test_quantity_is_validated_and_survives_owner_only_amendment():
    from services.api.domain import Candidate, validate_evidence, reduce_events
    from tests.test_domain import event as row

    text = "Approve 16 chairs for Room C."
    body = {**row("confirm", 1)["body"], **candidate(text, "16")}
    source = {"s": {"text": text, "revision": 1}}
    enrich_quantity(body, source)
    validate_evidence(Candidate.model_validate(body), source)
    forged = deepcopy(body)
    forged["quantity"]["unit"] = "beds"
    with pytest.raises(ValueError, match="quantity_parts_not_literal"):
        validate_evidence(Candidate.model_validate(forged), source)
    amendment = row("amend", 2, subject=body["subject"], owner="Mara", changed_fields=["owner"])
    projected = reduce_events([{"id": "1", "source_order": 1, "body": body}, amendment])[0]
    assert projected["value"] == "16 chairs"
    assert projected["quantity"] == body["quantity"]
    assert projected["owner"] == "Mara"


def test_explicit_literal_value_keeps_its_unit_among_negated_alternatives():
    from services.api.quantities import literal_candidates

    text = "The protocol says 7 kg, not 7 g."
    source = {"id": "s", "text": text, "revision": 1}
    assert {i["value"] for i in literal_candidates([source])} == {"7 kg", "7 g"}
    event = candidate(text, "7 kg")
    enrich_quantity(event, {"s": source})
    assert event["quantity"]["raw"] == "7 kg"
    assert event["quantity"]["unit"] == "kg"
