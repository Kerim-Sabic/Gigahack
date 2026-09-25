from scripts.variation_checks import check_variation


def test_variation_gate_rejects_missing_and_extra_commitments():
    gold = {"category": "action", "status": "confirmed", "due": "2027-02-04"}
    item = {"category": "action", "status": "confirmed", "due": "2027-02-04"}
    assert all(check_variation(gold, [], [item]).values())
    assert not all(check_variation(gold, [], []).values())
    assert not all(check_variation(gold, [], [item, item]).values())
    assert not all(check_variation(gold, [], [{**item, "due": "2027-02-02"}]).values())


def test_quantity_gold_requires_structured_unit_and_scope():
    gold = {
        "category": "decision",
        "status": "confirmed",
        "value": "9 desks",
        "unit": "desks",
        "scope_contains": "office r",
    }
    item = {"category": "decision", "status": "confirmed", "value": "9 desks", "subject": "Office R"}
    assert not all(check_variation(gold, [], [item]).values())
    item["quantity"] = {"unit": "desks"}
    assert all(check_variation(gold, [], [item]).values())
    item["subject"] = "Office S"
    assert not all(check_variation(gold, [], [item]).values())
