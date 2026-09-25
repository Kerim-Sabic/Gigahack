"""Local, source-preserving WER and explicitly annotated critical-span scoring.

This scores supplied transcripts, not recording quality or clinical acceptability.
Gold spans use token offsets so repeated names/numbers cannot match a different turn.
"""

import re
import unicodedata


CATEGORIES = {"name", "number", "unit", "negation", "medical_term", "date"}


def tokens(text):
    # Keep decimal separators, apostrophes and internal hyphens. Never convert digits,
    # transliterate scripts, strip accents or equate units/negation alternatives.
    return re.findall(r"\w+(?:[.,/'’\-]\w+)*", unicodedata.normalize("NFC", text).casefold())


def score(reference, hypothesis, critical_spans=()):
    ref, hyp = tokens(reference), tokens(hypothesis)
    if (len(ref) + 1) * (len(hyp) + 1) > 4_000_000:
        raise ValueError("alignment_too_large: score source-aligned clips separately; never truncate")
    # Deterministic Levenshtein alignment. Ties favor substitution, then deletion.
    costs = [list(range(len(hyp) + 1))]
    for i, word in enumerate(ref, 1):
        row = [i]
        for j, observed in enumerate(hyp, 1):
            row.append(min(costs[i - 1][j - 1] + (word != observed), costs[i - 1][j] + 1, row[-1] + 1))
        costs.append(row)
    i, j = len(ref), len(hyp)
    edits = []
    while i or j:
        if i and j and costs[i][j] == costs[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]):
            edits.append({"op": "equal" if ref[i - 1] == hyp[j - 1] else "substitute", "reference": i - 1, "hypothesis": j - 1})
            i, j = i - 1, j - 1
        elif i and costs[i][j] == costs[i - 1][j] + 1:
            edits.append({"op": "delete", "reference": i - 1, "hypothesis": None})
            i -= 1
        else:
            edits.append({"op": "insert", "reference": i, "hypothesis": j - 1})
            j -= 1
    edits.reverse()
    counts = {op: sum(e["op"] == op for e in edits) for op in ("substitute", "delete", "insert")}
    critical = {category: {"correct": 0, "annotated": 0} for category in sorted(CATEGORIES)}
    spans = []
    for span in critical_spans:
        start, end, category = span["start"], span["end"], span["category"]
        if category not in CATEGORIES or not (0 <= start < end <= len(ref)):
            raise ValueError("invalid_critical_span")
        if tokens(span["text"]) != ref[start:end]:
            raise ValueError("critical_span_reference_mismatch")
        # Interior insertion changes a multiword entity. Boundary insertions remain
        # visible in WER; their semantic effect still requires human adjudication.
        affected = [e for e in edits if e["op"] != "equal" and (
            start < e["reference"] < end if e["op"] == "insert" else start <= e["reference"] < end
        )]
        correct = not affected
        critical[category]["annotated"] += 1
        critical[category]["correct"] += correct
        spans.append({**span, "correct": correct, "edits": affected})
    return {
        "scope": "transcript alignment; supplied gold, not human or clinical validation",
        "normalization": "Unicode NFC and casefold; punctuation outside tokens ignored; numbers, units, accents and internal separators preserved",
        "reference_tokens": ref,
        "hypothesis_tokens": hyp,
        "word_errors": counts,
        "reference_word_count": len(ref),
        "wer": sum(counts.values()) / len(ref) if ref else None,
        "empty_reference_insertions": counts["insert"] if not ref else None,
        "critical_categories": critical,
        "critical_spans": spans,
        "alignment": edits,
        "semantic_support": "NOT MEASURED: alignment cannot assess meaning, speaker attribution or source ambiguity",
    }
