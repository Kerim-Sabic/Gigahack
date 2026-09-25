"""Literal quantity structure, independent of HTTP, persistence and model runtimes.

Units are recognized only beside the already extracted number inside an event's
own cited source. No conversion, arithmetic, cross-topic inheritance or new action.
"""

import re


NUMBER = r"[+-]?(?:\d{1,3}(?:[ ,\u00a0.]\d{3})+|\d+)(?:[.,]\d+)?"
UNITS = (
    "beds",
    "bed",
    "chairs",
    "chair",
    "desks",
    "desk",
    "pumps",
    "pump",
    "devices",
    "device",
    "monitors",
    "monitor",
    "filters",
    "filter",
    "paturi",
    "pat",
    "scaune",
    "scaun",
    "pompe",
    "pompă",
    "dispozitive",
    "кроватей",
    "кровати",
    "кровать",
    "коек",
    "койки",
    "койка",
    "насосов",
    "насоса",
    "насос",
    "euros",
    "euro",
    "EUR",
    "USD",
    "RON",
    "lei",
    "leu",
    "евро",
    "рублей",
    "рубля",
    "рубль",
    "dollars",
    "dollar",
    "pounds",
    "pound",
    "mg",
    "ml",
    "mL",
    "g",
    "kg",
    "µg",
    "μg",
    "mcg",
    "litres",
    "liters",
    "litre",
    "liter",
    "l",
    "mm",
    "cm",
    "m",
    "мг",
    "мл",
    "кг",
    "г",
    "%",
    "€",
    "$",
    "£",
)
_UNIT = "|".join(re.escape(u) for u in sorted(set(UNITS), key=len, reverse=True))
_NUMBER = re.compile(NUMBER)
_QUANTITY = re.compile(
    rf"(?<![\w.,])(?:(?P<prefix>[$€£])\s*)?(?P<amount>{NUMBER})"
    rf"(?:\s*(?:de\s+)?(?P<unit>{_UNIT})(?!\w))?",
    re.IGNORECASE,
)


def parts(raw):
    """Return exact lexical parts; never interpret decimal/thousands conventions."""
    match = _QUANTITY.fullmatch(raw)
    if not match:
        return None
    if match["prefix"] and match["unit"]:
        return None  # Two unit declarations require explicit review, not silent selection.
    return {"amount": match["amount"], "unit": match["prefix"] or match["unit"]}


def enrich_quantity(event, segments):
    """Attach an auditable quantity to an existing supported value, if unambiguous."""
    event.pop("quantity", None)  # Rebuild from the current field and citations, never stale metadata.
    value = event.get("value")
    if not value:
        return event
    numbers = _NUMBER.findall(value)
    if len(numbers) != 1:
        return event
    amount = numbers[0]
    options = {}
    for ref in event["evidence"]:
        if ref["field"] not in ("text", "value"):
            continue
        source = segments.get(ref["segment_id"])
        if not source or source["revision"] != ref["revision"] or source["text"].count(ref["quote"]) != 1:
            continue
        # A bare number cannot select between repeated mentions, including units
        # outside our recognized vocabulary. Do not prefer the recognized unit.
        declared = parts(value)
        if declared and not declared["unit"] and _NUMBER.findall(ref["quote"]).count(amount) > 1:
            event["uncertainties"].append(
                "Quantity unit/scope ambiguous in cited source; reviewer must resolve"
            )
            return event
        for match in _QUANTITY.finditer(ref["quote"]):
            raw = match[0]
            parsed = parts(raw)
            if not parsed or parsed["amount"] != amount or source["text"].count(raw) != 1:
                continue
            if declared and declared["unit"] and raw != value:
                continue  # Structure the already selected literal, never choose another unit.
            evidence = {**ref, "field": "value", "quote": raw}
            options[(parsed["amount"], parsed["unit"], raw)] = (parsed, evidence)
    with_units = {key: pair for key, pair in options.items() if pair[0]["unit"]}
    if with_units:
        options = with_units
    if len(options) != 1:
        if len(options) > 1:
            event["uncertainties"].append(
                "Quantity unit/scope ambiguous in cited source; reviewer must resolve"
            )
        return event
    (amount, unit, raw), (_, evidence) = next(iter(options.items()))
    uncertainties = [] if unit else ["Quantity unit not stated or not recognized; no unit was inferred"]
    event["quantity"] = {
        "amount": amount,
        "unit": unit,
        "scope": event["subject"],
        "raw": raw,
        "evidence": [evidence],
        "uncertainties": uncertainties,
    }
    event["value"] = raw
    event["evidence"] = [r for r in event["evidence"] if r["field"] != "value"] + [evidence]
    event["uncertainties"].extend(uncertainties)
    return event


def literal_candidates(segments):
    """Offer literal unit-bearing spans for model interpretation, never acceptance.

    Includes negated alternatives; only the model/reviewer can judge their meaning.
    """
    return [
        {"value": match[0], "segment_id": source["id"]}
        for source in segments
        for match in _QUANTITY.finditer(source["text"])
        if (match["prefix"] or match["unit"]) and parts(match[0]) and source["text"].count(match[0]) == 1
    ]
