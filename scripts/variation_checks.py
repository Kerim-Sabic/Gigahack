"""Gold-driven checks for separately versioned continuation variations.

These are exact automated field/state checks, not semantic or clinical adjudication.
"""


def check_variation(expected, events, projection):
    checks = {}
    active = [i for i in projection if i["status"] == "confirmed" and i["category"] in ("action", "decision")]
    selected = active
    if "category" in expected:
        selected = [i for i in active if i["category"] == expected["category"]]
        checks["exactly one expected commitment; no extra active commitments"] = (
            len(selected) == len(active) == 1
        )
    if expected.get("no_actions"):
        checks["no action or decision commitments"] = not active
    if "information_count" in expected:
        checks["separate information facts"] = (
            sum(i["category"] == "information" and i["status"] == "information" for i in projection)
            == expected["information_count"]
        )
    target = selected[0] if len(selected) == 1 else None
    for key in ("status", "owner", "due", "value"):
        if key in expected:
            checks["correct " + key] = target is not None and target.get(key) == expected[key]
    if expected.get("pending"):
        checks["tentative alternative retained"] = target is not None and bool(target.get("pending"))
    if "unit" in expected:
        checks["structured literal unit"] = (
            target is not None and (target.get("quantity") or {}).get("unit") == expected["unit"]
        )
    if "scope_contains" in expected:
        checks["scope retained"] = (
            target is not None and expected["scope_contains"].casefold() in target["subject"].casefold()
        )
    if "quantity_contains" in expected:
        candidates = [target] if target else projection
        checks["quantity retained"] = any(
            expected["quantity_contains"] in (i.get("value") or "") for i in candidates
        )
    if not checks:
        raise ValueError("Variation has no applicable gold checks")
    return checks
