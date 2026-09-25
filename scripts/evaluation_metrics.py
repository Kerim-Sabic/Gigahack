"""Explicitly scoped automated metrics for annotated synthetic text variations."""


def measure(rows, cases):
    gold = {case["id"]: case["expected"] for case in cases}
    counts = {
        category: {"true_positive": 0, "false_positive": 0, "false_negative": 0}
        for category in ("action", "decision")
    }
    fields = {
        field: {"correct": 0, "annotated": 0}
        for field in ("owner", "due", "value", "unit", "scope_contains", "status", "quantity_contains", "pending")
    }
    candidates = warned = action_count = missing_owner = missing_due = evidence_valid = 0
    for row in rows:
        expected = gold[row["id"]]
        events = row.get("events", [])
        candidates += len(events)
        warned += sum(bool(e.get("uncertainties")) for e in events)
        evidence_valid += bool(row.get("checks", {}).get("literal evidence valid"))
        active = [
            item
            for item in row.get("projection", [])
            if item["status"] == "confirmed" and item["category"] in counts
        ]
        actions = [item for item in active if item["category"] == "action"]
        action_count += len(actions)
        missing_owner += sum(i.get("owner") is None for i in actions)
        missing_due += sum(i.get("due") is None for i in actions)
        expected_category = expected.get("category")
        selected = [i for i in active if i["category"] == expected_category]
        target = selected[0] if len(selected) == 1 else None
        matches = {}
        for field, totals in fields.items():
            if field not in expected:
                continue
            totals["annotated"] += 1
            if field == "quantity_contains":
                pool = [target] if target else ([] if expected_category else row.get("projection", []))
                correct = any(expected[field] in (item.get("value") or "") for item in pool)
            elif field == "pending":
                correct = target is not None and bool(target.get("pending")) == expected[field]
            elif field == "unit":
                correct = target is not None and (target.get("quantity") or {}).get("unit") == expected[field]
            elif field == "scope_contains":
                correct = target is not None and expected[field].casefold() in target["subject"].casefold()
            else:
                correct = target is not None and target.get(field) == expected[field]
            totals["correct"] += bool(correct)
            matches[field] = correct
        for category, totals in counts.items():
            predictions = sum(i["category"] == category for i in active)
            wanted = int(expected_category == category)
            matched = int(wanted and target is not None and all(matches.values()))
            totals["true_positive"] += matched
            totals["false_positive"] += predictions - matched
            totals["false_negative"] += wanted - matched
    for totals in counts.values():
        tp, fp, fn = totals["true_positive"], totals["false_positive"], totals["false_negative"]
        totals["precision"] = tp / (tp + fp) if tp + fp else None
        totals["recall"] = tp / (tp + fn) if tp + fn else None
    return {
        "scope": "strict annotated final-commitment matching on synthetic text; not semantic adjudication or audio accuracy",
        "matching_rule": "correct category, one same-category commitment, and all annotated owner/date/value/unit/scope/status fields; extra predictions count as false positives",
        "commitments": counts,
        "annotated_fields": fields,
        "final_case_outcome": {
            "correct": sum(row["status"].startswith("PASS") for row in rows),
            "total": len(rows),
        },
        "literal_evidence": {"valid_cases": evidence_valid, "total_cases": len(rows)},
        "uncertainty": {
            "warned_candidates": warned,
            "candidates": candidates,
            "missing_owner_active_actions": missing_owner,
            "missing_deadline_active_actions": missing_due,
            "active_actions": action_count,
        },
        "unsupported_semantic_statements": "NOT MEASURED: requires source-meaning adjudication; literal citations alone do not prove support",
        "human_corrections_and_review_time": "NOT MEASURED: automated failed checks are not observed human edits",
    }
