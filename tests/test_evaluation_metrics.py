from scripts.evaluation_metrics import measure


def test_metrics_penalize_omissions_extras_and_wrong_fields():
    cases = [{"id": "a", "expected": {"category": "action", "due": "2027-01-02"}}]
    good = {"category": "action", "status": "confirmed", "due": "2027-01-02"}
    row = {"id": "a", "status": "PASS", "projection": [good], "checks": {"literal evidence valid": True}}
    assert measure([row], cases)["commitments"]["action"]["recall"] == 1
    wrong = {**row, "status": "FAIL", "projection": [{**good, "due": None}]}
    assert measure([wrong], cases)["commitments"]["action"]["recall"] == 0
    extra = {**row, "projection": [good, good], "status": "FAIL"}
    assert measure([extra], cases)["commitments"]["action"]["false_positive"] == 2
    empty = {**row, "projection": [], "status": "FAIL"}
    m = measure([empty], cases)["commitments"]["action"]
    assert m["precision"] is None and m["recall"] == 0


def test_partial_quantity_annotation_and_pending_alternative_are_scored():
    cases = [{"id": "a", "expected": {"category": "decision", "quantity_contains": "34", "pending": True}}]
    row = {"id": "a", "status": "FAIL", "projection": [{"category": "decision", "status": "confirmed", "value": "30 beds", "pending": []}]}
    report = measure([row], cases)
    assert report["commitments"]["decision"]["recall"] == 0
    assert report["annotated_fields"]["quantity_contains"] == {"correct": 0, "annotated": 1}
