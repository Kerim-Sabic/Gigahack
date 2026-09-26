import hashlib
import json

import pytest

from services.api.db import transaction
from services.api.transcript_import import parse_transcript
from tests.test_api import client, audio, new_meeting  # noqa: F401


def test_import_preserves_original_and_overlapping_out_of_order_anchors(client):  # noqa: F811
    meeting = new_meeting(client)
    base = '/api/v1/meetings/' + meeting['id']
    asset = client.post(base + '/uploads', files={'file': ('test.wav', audio(), 'audio/wav')}).json()['id']
    source = 'Speaker 1\r\n0:01\r\nJapanese\r\nBună.\r\n\r\nSpeaker 2\r\n0:00\r\nДа.\r\n\r\nSpeaker 3\r\n0:01\r\nBine.'
    body = {'asset_id': asset, 'revision': meeting['revision'], 'source': source, 'filename': '../../test.txt'}
    response = client.post(base + '/transcript-imports', json=body)
    assert response.status_code == 200, response.text
    assert response.json()['segments'] == 3
    rows = client.get(base + '/transcript').json()
    assert [r['start'] for r in rows] == [0, 16000, 16000]
    assert [r['end'] for r in rows] == [16000, 32000, 32000]
    assert all(r['words'] == '[]' for r in rows)
    tagged = next(r for r in rows if r['speaker'] == 'Speaker 1')
    assert tagged['text'] == 'Bună.'
    raw = json.loads(tagged['raw'])
    assert raw['source_index'] == 0 and raw['supplied_language_labels'] == ['Japanese']
    assert raw['verified_against_audio'] is False
    with transaction() as c:
        from pathlib import Path
        folder = Path(c.execute('SELECT path FROM assets WHERE id=?', (asset,)).fetchone()[0]).parent
    saved = folder / ('transcript-' + hashlib.sha256(source.encode()).hexdigest() + '.txt')
    assert saved.read_bytes() == source.encode()
    assert client.post(base + '/transcript-imports', json=body).json()['already_imported']
    assert client.post(base + '/transcript-imports', json={**body, 'source': source + '!'}).status_code == 409
    assert client.get(base).json()['transcript_pending_assets'] == [asset]


@pytest.mark.parametrize('source', ['unstructured text', 'Speaker 1\n0:02\nOutside', 'Speaker 1\n0:99\nBad', 'Speaker 1\n0:00\n'])
def test_invalid_import_is_rejected(source):
    with pytest.raises(ValueError):
        parse_transcript(source, 32000, 16000)


def test_import_requires_meeting_membership_and_current_revision(client):  # noqa: F811
    meeting = new_meeting(client)
    base = '/api/v1/meetings/' + meeting['id']
    asset = client.post(base + '/uploads', files={'file': ('test.wav', audio(), 'audio/wav')}).json()['id']
    body = {'asset_id': asset, 'revision': 999, 'source': 'Speaker 1\n0:00\nBună.', 'filename': 'test.txt'}
    assert client.post(base + '/transcript-imports', json=body).status_code == 409
    assert client.post('/api/v1/meetings/unknown/transcript-imports', json=body).status_code == 404
    assert client.get(base + '/transcript').json() == []


def test_meeting_time_notes_persist_and_validate(client):  # noqa: F811
    response = client.post('/api/v1/meetings', json={'title': 'Test', 'time': '17:25', 'notes': 'Draft only'})
    assert response.status_code == 200
    assert response.json()['time'] == '17:25' and response.json()['notes'] == 'Draft only'
    meeting = response.json()
    edited = client.patch('/api/v1/meetings/' + meeting['id'], json={'title': 'Renamed', 'revision': meeting['revision']})
    assert edited.json()['time'] == '17:25' and edited.json()['notes'] == 'Draft only'
    assert client.post('/api/v1/meetings', json={'title': 'Test', 'time': '24:99'}).status_code == 422


def test_source_draft_requires_exact_evidence_and_leaves_review_separate(client):  # noqa: F811
    meeting = new_meeting(client)
    base = '/api/v1/meetings/' + meeting['id']
    asset = client.post(base + '/uploads', files={'file': ('test.wav', audio(), 'audio/wav')}).json()['id']
    client.post(base + '/transcript-imports', json={'asset_id': asset, 'revision': 1,
                'source': 'Speaker 1\n0:00\nVerificăm raportul.', 'filename': 'test.txt'}).raise_for_status()
    segment = client.get(base + '/transcript').json()[0]
    event = {'subject': 'report', 'category': 'action', 'kind': 'propose', 'text': 'Check report',
             'evidence': [{'segment_id': segment['id'], 'revision': 1, 'field': 'text', 'quote': 'Invented'}]}
    body = {'asset_id': asset, 'revision': 2, 'source_versions': {segment['id']: 1},
            'events': [event], 'reason': 'Source-based draft, not model output'}
    assert client.post(base + '/transcript-draft', json=body).status_code == 422
    event['evidence'][0]['quote'] = segment['text']
    assert client.post(base + '/transcript-draft', json={**body, 'source_versions': {}}).status_code == 409
    assert client.post(base + '/transcript-draft', json=body).status_code == 200
    result = client.get(base + '/items').json()
    assert len(result['candidates']) == 1 and result['candidates'][0]['review'] == 'unreviewed'
    assert client.get(base).json()['transcript_pending_assets'] == []
    assert client.post(base + '/snapshots', json={'revision': 3}).status_code == 409
    with transaction() as c:
        assert c.execute('SELECT COUNT(*) FROM approvals').fetchone()[0] == 0
        assert c.execute('SELECT COUNT(*) FROM accepted_events').fetchone()[0] == 0
