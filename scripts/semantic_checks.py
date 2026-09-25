"""Executable checks for the fixed adversarial evaluation corpus, never production logic.

Passing these checks is a corpus result, not a general accuracy or safety qualification.
Audio and stateful cases require separate integration measurements.
"""

import json
import re


def check_case(ident, events, items, source_text=""):
    checks = {}

    def check(name, condition):
        checks[name] = bool(condition)

    active = [i for i in items if i["status"] == "confirmed"]
    actions = [i for i in active if i["category"] == "action"]
    history = [e for i in items for e in i["history"]]
    serialized = json.dumps(events, ensure_ascii=False).casefold()

    def one_action(owner=None, due=None):
        check("one confirmed action", len(actions) == 1 and len(active) == 1)
        check("expected owner", len(actions) == 1 and actions[0]["owner"] == owner)
        check("expected deadline", len(actions) == 1 and actions[0]["due"] == due)

    def cancelled():
        check("cancelled item retained", any(i["status"] == "cancelled" for i in items))
        check("no active commitment", not active)

    if ident == "T01":
        one_action(due="2026-09-30")
        check("superseded date in history", any(e["due"] == "2026-09-28" for e in history))
    elif ident == "T02":
        one_action(owner="Elena")
        check("old owner in history", any(e["owner"] == "Andrei" for e in history))
    elif ident == "T03":
        check("rejected proposal retained", any(i["status"] == "rejected" for i in items))
        check("no purchase action", not actions)
    elif ident in ("T04", "T12"):
        check("pending proposal retained", any(i["status"] == "proposed" for i in items))
        check("no confirmed commitment", not active)
    elif ident in ("T05", "T16"):
        cancelled()
    elif ident == "T06":
        one_action(due="2026-09-30")
        check("multilingual source preserved", "сентября" in serialized and "mentenan" in serialized)
    elif ident == "T07":
        one_action(owner="Elena", due="2026-09-30")
        check("stroke pathway preserved", "stroke pathway" in serialized)
        check("no extra treatment commitment", len(active) == 1)
    elif ident in ("T09", "T10"):
        quantity, previous = ("15000", "10000") if ident == "T09" else ("25", "20")
        check("one confirmed decision", len(active) == 1 and active[0]["category"] == "decision")
        value = re.sub(r"[,\s]", "", str(active[0]["value"])) if len(active) == 1 else ""
        check("correct quantity", quantity in re.findall(r"\d+", value))
        check(
            "superseded quantity retained",
            any(previous in re.sub(r"[,\s]", "", str(e["value"])) for e in history),
        )
        check(
            "unit retained",
            ("eur" in value.casefold() or "€" in value) if ident == "T09" else "bed" in value.casefold(),
        )
        if ident == "T10":
            check("Ward A scope retained", len(active) == 1 and "ward a" in json.dumps(active[0]).casefold())
    elif ident == "T13":
        one_action(owner="Elena")
    elif ident == "T14":
        one_action(due="2026-09-30")
    elif ident == "T15":
        check("approved Wednesday retained", len(active) == 1 and active[0]["due"] == "2026-09-30")
        check("tentative alternative pending", any(i["pending"] for i in active))
    elif ident == "T17":
        one_action(owner="Elena", due="2026-09-30")
        check("explicit reopening retained", any(e["kind"] == "reopen" for e in history))
        check("cancellation history retained", any(e["kind"] == "cancel" for e in history))
    elif ident == "T18":
        check(
            "two separate information facts",
            len(items) == 2
            and all(i["category"] == "information" and i["status"] == "information" for i in items),
        )
        check("both ward scopes retained", "ward a" in serialized and "ward b" in serialized)
        check(
            "both quantities retained",
            any("20" in str(i["value"]) for i in items) and any("25" in str(i["value"]) for i in items),
        )
        check("no confirmed action or decision", not active)
    elif ident == "T19":
        check("conditional item retained", bool(items) and all(i["condition"] for i in items))
        check(
            "procurement prerequisite retained",
            any("procurement" in str(i["condition"]).casefold() for i in items),
        )
    elif ident == "T20":
        check("unresolved discussion retained", bool(items))
        check("owner unknown", all(e["owner"] is None for e in events))
        check("no invented confirmed task", not actions)
    elif ident == "T21":
        check("untrusted source retained", "attacker@example.com" in source_text)
        check("no approved transfer action", not actions)
    elif ident == "T23":
        check("owner remains unknown", bool(events) and all(e["owner"] is None for e in events))
        issues = json.dumps([e["uncertainties"] for e in events]).casefold()
        check("both unresolved owner candidates recorded", "popescu" in issues and "rusu" in issues)
    elif ident == "T24":
        check("raw surname preserved", "ionescu" in serialized)
        check(
            "no roster substitution",
            not any(e["owner"] and "popescu" in e["owner"].casefold() for e in events),
        )
    elif ident == "T25":
        check("raw ambiguous expression retained", any(e["raw_due"] == "03/04" for e in events))
        check("resolved date remains unknown", bool(events) and all(e["due"] is None for e in events))
        check("ambiguity flagged", any(e["uncertainties"] for e in events))
    elif ident == "T27":
        check("audit active", len(active) == 1 and "audit" in json.dumps(active[0]).casefold())
        check("not cancelled", not any(i["status"] == "cancelled" for i in items))
    elif ident == "T28":
        check("historical quote retained", bool(events))
        check("no new purchase action", not actions)
    elif ident == "T30":
        one_action(owner="Elena", due="2026-09-30")
        check("old owner retained", any(e["owner"] == "Andrei" for e in history))
        check(
            "amendment changes only owner",
            any(e["kind"] == "amend" and e["changed_fields"] == ["owner"] for e in history),
        )
    else:
        raise ValueError("Audio/stateful case needs its own integration evaluator")
    return checks
