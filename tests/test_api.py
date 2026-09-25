import io
import json
import time
import wave

import pytest
from fastapi.testclient import TestClient

from services.api import config
from services.api.db import canonical, transaction, uid
from services.api.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'DATA', tmp_path)
    with TestClient(app) as c:
        r = c.post('/api/v1/setup', json={'name': 'secretary', 'password': 'synthetic-password-123'})
        assert r.status_code == 200, r.text
        c.headers['x-csrf-token'] = r.json()['csrf']
        yield c


def new_meeting(c):
    r = c.post('/api/v1/meetings', json={'title': 'Synthetic maintenance', 'date': '2026-09-25', 'participants': ['Elena', 'Andrei']})
    assert r.status_code == 200, r.text
    return r.json()


def audio():
    stream = io.BytesIO()
    with wave.open(stream, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b'\x00\x00' * 32000)
    return stream.getvalue()


def seed_candidate(c, m):
    """Explicit test setup only; no production fixture selector."""
    r = c.post(f'/api/v1/meetings/{m["id"]}/uploads', files={'file': ('synthetic.wav', audio(), 'audio/wav')})
    assert r.status_code == 200, r.text
    asset = r.json()['id']
    sid, cid = uid(), uid()
    text = 'Elena sends the report. Confirmed.'
    event = dict(subject='report', category='action', kind='confirm', text='Send report', owner='Elena', due=None,
                 raw_due=None, condition=None, value=None, changed_fields=[], uncertainties=[],
                 evidence=[dict(segment_id=sid, revision=1, field='owner', quote='Elena'),
                           dict(segment_id=sid, revision=1, field='text', quote=text)])
    with transaction() as db:
        db.execute('INSERT INTO segments(id,meeting_id,asset_id,revision,start,end,text,raw) VALUES(?,?,?,1,0,32000,?,?)', (sid, m['id'], asset, text, text))
        db.execute('INSERT INTO candidates(id,meeting_id,subject,body,source_order,created) VALUES(?,?,?,?,0,?)', (cid, m['id'], 'report', canonical(event), time.time()))
        db.execute('INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?)', (uid(), m['id'], cid, sid, 1, 'owner', 'Elena', 0, 5))
    return sid, cid, asset


def test_review_snapshot_approval_delivery_and_staleness(client):
    m = new_meeting(client)
    sid, cid, _ = seed_candidate(client, m)
    base = f'/api/v1/meetings/{m["id"]}'
    assert client.post(base + '/snapshots', json={'revision': 1}).status_code == 409
    r = client.post(f'/api/v1/review-issues/{cid}/resolve', json={'revision': 1, 'action': 'accepted'})
    assert r.status_code == 200, r.text
    snap = client.post(base + '/snapshots', json={'revision': 2}).json()['id']
    group = client.get('/api/v1/recipient-groups').json()[0]
    body = {'group_id': group['id'], 'group_version': group['version']}
    assert client.post(f'/api/v1/snapshots/{snap}/deliveries', json=body).status_code == 409
    assert client.post(f'/api/v1/snapshots/{snap}/approve', json={'revision': 2}).status_code == 200
    sent = client.post(f'/api/v1/snapshots/{snap}/deliveries', json=body)
    assert sent.status_code == 200, sent.text
    duplicate = client.post(f'/api/v1/snapshots/{snap}/deliveries', json=body)
    assert duplicate.json()['id'] == sent.json()['id']
    assert client.get(f'/api/v1/snapshots/{snap}/exports/json').json()['items'][0]['owner'] == 'Elena'
    assert client.post(f'/api/v1/segments/{sid}/revisions', json={'revision': 1, 'text': 'Andrei sends the report.'}).status_code == 200
    assert client.get(base + '/items').json()['items'] == []
    assert client.post(f'/api/v1/snapshots/{snap}/approve', json={'revision': 2}).status_code == 409
    assert client.post(f'/api/v1/snapshots/{snap}/deliveries', json=body).status_code == 409
    assert client.get(f'/api/v1/snapshots/{snap}/exports/json').json()['items'][0]['owner'] == 'Elena'


def test_admin_has_no_implicit_content_access(client):
    m = new_meeting(client)
    _, _, asset = seed_candidate(client, m)
    client.post('/api/v1/accounts', json={'name': 'another-admin', 'password': 'another-password-123', 'role': 'admin'})
    client.delete('/api/v1/sessions/current')
    client.headers.pop('x-csrf-token')
    r = client.post('/api/v1/sessions', json={'name': 'another-admin', 'password': 'another-password-123'})
    client.headers['x-csrf-token'] = r.json()['csrf']
    for route in [f'meetings/{m["id"]}', f'meetings/{m["id"]}/transcript', f'meetings/{m["id"]}/items', f'assets/{asset}/audio']:
        assert client.get('/api/v1/' + route).status_code == 404
    assert client.get('/api/v1/meetings').json() == []


def test_chunk_ack_idempotency_and_gap_rejection(client):
    m = new_meeting(client)
    rid = client.post(f'/api/v1/meetings/{m["id"]}/recordings', json={'sample_rate': 16000}).json()['id']
    url = f'/api/v1/recordings/{rid}/chunks/0'
    r = client.put(url, content=b'\x00\x00' * 32000)
    assert r.status_code == 200, r.text
    assert r.json()['acknowledged_samples'] == 32000
    assert client.put(url, content=b'\x00\x00' * 32000).json() == r.json()
    assert client.put(url, content=b'\x01\x00' * 32000).status_code == 409
    assert client.post(f'/api/v1/recordings/{rid}/finish', json={'count': 2}).status_code == 409
    assert client.post(f'/api/v1/recordings/{rid}/finish', json={'count': 1, 'gaps': []}).status_code == 200


def test_csrf_and_origin(client):
    assert client.post('/api/v1/meetings', json={}, headers={'origin': 'https://attacker.test'}).status_code == 403
    client.headers.pop('x-csrf-token')
    assert client.post('/api/v1/meetings', json={}).status_code == 403


def test_restart_preserves_state(client):
    m = new_meeting(client)
    from services.api.db import migrate
    migrate()
    assert client.get(f'/api/v1/meetings/{m["id"]}').json()['title'] == m['title']


def test_adversarial_spec_inventory():
    from pathlib import Path
    cases = json.loads(Path('tests/fixtures/adversarial.json').read_text(encoding='utf-8'))
    assert [c['id'] for c in cases] == [f'T{i:02}' for i in range(1, 31)]
    assert all(c['expected'] for c in cases)
