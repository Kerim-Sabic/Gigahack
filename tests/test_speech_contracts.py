import pytest
from pydantic import ValidationError

from services.speech.contracts import ASRResult
from services.speech.context import ContextBuilder


def result(**changes):
    return ASRResult(**({
        'engine': 'test', 'model': 'test', 'model_version': 'fixture',
        'runtime': 'none', 'precision': 'none', 'device': 'none',
        'text': 'Принимайте după masă.', 'start_sample': 16000,
        'end_sample': 48000, 'latency_ms': 1,
    } | changes))


def test_missing_timing_and_confidence_remain_explicit_and_native_text_survives():
    value = result()
    assert value.words is None and value.confidence is None
    assert value.language_spans == []
    assert ASRResult.model_validate_json(value.model_dump_json()).text == value.text


@pytest.mark.parametrize('changes', [
    {'confidence': .99},
    {'confidence_basis': 'validated_calibration'},
    {'latency_ms': float('nan')},
    {'end_sample': 16000},
    {'words': [{'text': 'test', 'start_sample': 0, 'end_sample': 10, 'timing_source': 'test'}]},
    {'language_spans': [{'language': 'ro', 'start_char': 0, 'end_char': 100, 'basis': 'model'}]},
    {'language_spans': [{'language': 'ro', 'start_char': 0, 'end_char': 1, 'basis': 'model', 'start_sample': 16000}]},
    {'language_spans': [
        {'language': 'ru', 'start_char': 0, 'end_char': 4, 'basis': 'model'},
        {'language': 'ro', 'start_char': 3, 'end_char': 6, 'basis': 'model'},
    ]},
])
def test_invalid_evidence_is_rejected(changes):
    with pytest.raises(ValidationError):
        result(**changes)


def test_context_empty_by_default_deduplicated_without_invented_terms():
    builder = ContextBuilder()
    assert builder.build() == ''
    prompt = builder.build(participants=['Ирина'], user_terms=[' după masă ', 'Ирина'])
    assert prompt.count('Ирина') == 1
    assert 'după masă' in prompt


@pytest.mark.parametrize('terms', [[''], ['x\ny'], [None], ['x' * 1024]])
def test_context_invalid_or_oversize_is_rejected_not_silently_truncated(terms):
    with pytest.raises(ValueError):
        ContextBuilder().build(user_terms=terms)


@pytest.mark.parametrize('terms', ['după masă', {'Ирина': True}, None, ['x'] * 257])
def test_context_rejects_wrong_container_or_excessive_terms(terms):
    with pytest.raises(ValueError):
        ContextBuilder().build(user_terms=terms)


@pytest.mark.parametrize('budget', [True, 63, 4097, 1024.0])
def test_context_rejects_invalid_budget(budget):
    with pytest.raises(ValueError):
        ContextBuilder(budget)
