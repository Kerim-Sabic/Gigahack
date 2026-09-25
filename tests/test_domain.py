import pytest

from services.api.domain import Candidate, reduce_events, validate_evidence


def event(kind, order, **kwargs):
    return {'id': str(order), 'source_order': order, 'body': {'subject': 'maintenance', 'category': 'action',
        'kind': kind, 'text': 'Maintenance', 'owner': None, 'due': None, 'condition': None, 'value': None,
        'changed_fields': [], 'uncertainties': [], 'evidence': [], **kwargs}}


def test_late_ingestion_replays_source_and_preserves_other_fields():
    events = [event('amend', 2, owner='Elena', changed_fields=['owner']),
              event('confirm', 1, owner='Andrei', due='2026-09-30')]
    item = reduce_events(events)[0]
    assert (item['owner'], item['due']) == ('Elena', '2026-09-30')


def test_proposal_does_not_replace_active_and_cancel_requires_reopen():
    events = [event('confirm', 1, due='2026-09-30'), event('propose', 2, due='2026-10-02')]
    assert reduce_events(events)[0]['due'] == '2026-09-30'
    events += [event('cancel', 3), event('confirm', 4)]
    assert reduce_events(events)[0]['status'] == 'cancelled'
    events += [event('reopen', 5, owner='Elena')]
    assert reduce_events(events)[0]['status'] == 'confirmed'


def test_rejected_is_not_active_and_condition_survives():
    assert reduce_events([event('propose', 1), event('reject', 2)])[0]['status'] == 'rejected'
    item = reduce_events([event('confirm', 1, condition='If procurement approves'), event('amend', 2, owner='Elena', changed_fields=['owner'])])[0]
    assert item['condition'] == 'If procurement approves'


def test_evidence_unicode_and_ambiguity():
    body = event('confirm', 1)['body']
    body['evidence'] = [{'segment_id': 's', 'revision': 1, 'field': 'text', 'quote': 'ședința'}]
    candidate = Candidate.model_validate(body)
    assert validate_evidence(candidate, {'s': {'revision': 1, 'text': 'O ședința'}})[0]['start'] == 2
    with pytest.raises(ValueError):
        validate_evidence(candidate, {'s': {'revision': 1, 'text': 'ședința ședința'}})
    with pytest.raises(ValueError):
        validate_evidence(candidate, {'s': {'revision': 2, 'text': 'ședința'}})
