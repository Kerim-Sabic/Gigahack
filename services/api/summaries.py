"""Membership-checked, source-versioned local LLM meeting summaries."""
import hashlib
import json
import time

from fastapi import APIRouter, Depends
from typing import Literal
from pydantic import BaseModel, Field

from .db import canonical, transaction, uid, audit
from .minutes import authenticated
from .domain import Strict
from .provenance import runtime_identity

router = APIRouter(prefix='/api/v1')


class SummaryPoint(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    source_ids: list[str] = Field(min_length=1, max_length=32)


class SummaryBody(BaseModel):
    points: list[SummaryPoint] = Field(min_length=1, max_length=12)


def sources(c, ident):
    return [dict(r) for r in c.execute(
        'SELECT id,asset_id,revision,start,end,text,speaker FROM segments WHERE meeting_id=? ORDER BY asset_id,start,id', (ident,))]


def source_hash(meeting, segments):
    return hashlib.sha256(canonical({'segments': segments, 'meeting': {
        k: meeting[k] for k in ('title', 'date', 'timezone', 'language')
    }}).encode()).hexdigest()


def current_summary(c, meeting):
    row = c.execute('SELECT * FROM meeting_summaries WHERE meeting_id=? ORDER BY created DESC,rowid DESC LIMIT 1', (meeting['id'],)).fetchone()
    if not row:
        return None
    return {**dict(row), 'body': json.loads(row['body']), 'stale': row['source_hash'] != source_hash(meeting, sources(c, meeting['id']))}


@router.get('/meetings/{ident}/summary')
def get_summary(ident: str, u=Depends(authenticated)):
    from .main import access
    with transaction() as c:
        meeting = access(c, ident, u)
        job = c.execute("SELECT id,state,error FROM jobs WHERE meeting_id=? AND json_extract(config,'$.summary_only')=1 ORDER BY created DESC,rowid DESC LIMIT 1", (ident,)).fetchone()
        return {'summary': current_summary(c, meeting), 'job': dict(job) if job else None,
                'has_transcript': bool(c.execute("SELECT 1 FROM segments WHERE meeting_id=? AND trim(text)!='' LIMIT 1", (ident,)).fetchone())}


class SummaryRequest(Strict):
    revision: int
    device: Literal['cuda', 'cpu'] = 'cuda'


@router.post('/meetings/{ident}/summary')
def queue_summary(ident: str, body: SummaryRequest, u=Depends(authenticated)):
    from .main import access, fail
    from services.worker.settings import load_settings
    with transaction() as c:
        meeting = access(c, ident, u, True)
        if meeting['revision'] != body.revision:
            fail('revision_conflict', 409)
        if c.execute("SELECT 1 FROM jobs WHERE meeting_id=? AND state IN ('queued','running')", (ident,)).fetchone():
            fail('processing_incomplete', 409)
        segments = sources(c, ident)
        if not any(s['text'].strip() for s in segments):
            fail('transcript_required', 409)
        job = uid()
        settings = {'device': body.device, 'inference': load_settings().model_dump(),
                    'summary_only': True, 'transcript_only': True, 'implementation': runtime_identity(),
                    'summary_source_hash': source_hash(meeting, segments)}
        c.execute("INSERT INTO jobs(id,meeting_id,asset_id,state,stage,config,created) VALUES(?,?,?,'queued','queued',?,?)",
                  (job, ident, segments[0]['asset_id'], canonical(settings), time.time()))
        audit(c, ident, u['id'], 'meeting_summary_requested', {'job': job})
        return {'id': job, 'state': 'queued'}


def process_summary(job, spec, run_stage):
    with transaction() as c:
        meeting = dict(c.execute('SELECT * FROM meetings WHERE id=?', (job['meeting_id'],)).fetchone())
        segments = sources(c, meeting['id'])
    expected = spec['config']['summary_source_hash']
    if source_hash(meeting, segments) != expected:
        raise RuntimeError('summary_source_changed')
    spec['segments'] = segments
    spec['meeting'] = meeting
    result = SummaryBody.model_validate(run_stage(job, 'extract', spec)).model_dump()
    known = {s['id'] for s in segments}
    if any(not set(p['source_ids']) <= known for p in result['points']):
        raise RuntimeError('summary_invalid_source')
    with transaction() as c:
        latest = dict(c.execute('SELECT * FROM meetings WHERE id=?', (meeting['id'],)).fetchone())
        if source_hash(latest, sources(c, meeting['id'])) != expected:
            raise RuntimeError('summary_source_changed')
        c.execute('INSERT INTO meeting_summaries VALUES(?,?,?,?,?,?)',
                  (uid(), meeting['id'], job['id'], expected, canonical(result), time.time()))
        c.execute("UPDATE jobs SET state='complete',stage='awaiting_review',lease=0 WHERE id=?", (job['id'],))
        c.execute("UPDATE meetings SET status='awaiting_review',revision=revision+1 WHERE id=?", (meeting['id'],))
