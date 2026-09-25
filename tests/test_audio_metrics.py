import pytest
import json

from scripts.audio_metrics import score, tokens


def test_numbers_units_names_and_negation_are_not_normalized_away():
    reference = "Elena says 0.5 mg, not 5 ml."
    spans = [
        {"start": 0, "end": 1, "text": "Elena", "category": "name"},
        {"start": 2, "end": 3, "text": "0.5", "category": "number"},
        {"start": 3, "end": 4, "text": "mg", "category": "unit"},
        {"start": 4, "end": 5, "text": "not", "category": "negation"},
    ]
    report = score(reference, "Alina says 5 ml and 5 ml", spans)
    assert report["word_errors"] == {"substitute": 4, "delete": 0, "insert": 0}
    assert report["wer"] == 4 / 7
    assert all(not span["correct"] for span in report["critical_spans"])


def test_multilingual_accents_and_decimal_separators_preserved():
    assert tokens("Ședință среда 0,5 0.5 03/04") == ["ședință", "среда", "0,5", "0.5", "03/04"]
    assert score("ședință", "sedinta")["wer"] == 1
    assert score("0,5", "0.5")["wer"] == 1
    assert score("03/04", "03 04")["wer"] != 0


def test_empty_reference_and_omitted_transcript_are_not_perfect():
    assert score("", "thank you")["wer"] is None
    assert score("", "thank you")["empty_reference_insertions"] == 2
    assert score("not approved", "")["wer"] == 1
    with pytest.raises(ValueError, match="alignment_too_large"):
        score("word " * 2000, "word " * 2000)


def test_repeated_entities_scored_at_annotated_occurrence_and_insertions_exposed():
    span = {"start": 3, "end": 5, "text": "Elena Rusu", "category": "name"}
    assert not score("Elena Rusu or Elena Rusu", "Elena Rusu or Elena Popescu", [span])["critical_spans"][0]["correct"]
    interior = {"start": 0, "end": 2, "text": "Elena Rusu", "category": "name"}
    assert not score("Elena Rusu", "Elena and Rusu", [interior])["critical_spans"][0]["correct"]
    with pytest.raises(ValueError, match="reference_mismatch"):
        score("Elena Rusu", "Elena Rusu", [{**interior, "text": "Alina Rusu"}])


def test_scorer_retains_supplied_provenance_and_requires_observed_segments(tmp_path):
    from scripts.score_audio import build_report

    reference, observed = tmp_path / "gold.json", tmp_path / "asr.json"
    reference.write_text(json.dumps({"reference_text": "not approved", "provenance": {"review_status": "unreviewed synthetic script"}}))
    observed.write_text(json.dumps({"segments": [{"text": "approved"}]}))
    report = build_report(reference, observed)
    assert report["wer"] == 0.5
    assert report["inference_performed_by_this_command"] is False
    assert report["reference_provenance_as_supplied"]["review_status"] == "unreviewed synthetic script"
    assert len(report["observed_output_sha256"]) == 64
