"""Run real, offline ASR on separately annotated local clips (Linux/WSL)."""

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def network_probe():
    result = {}
    for family,address in ((socket.AF_INET,('1.1.1.1',443)),(socket.AF_INET6,('2606:4700:4700::1111',443))):
        with socket.socket(family,socket.SOCK_STREAM) as connection:
            connection.settimeout(2)
            try:
                connection.connect(address)
            except OSError as exc:
                result[str(family)] = exc.errno
            else:
                raise RuntimeError('external_network_available')
    return result


def validate_cases(path):
    from services.api.audio import sha

    cases=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(cases,list) or not 1 <= len(cases) <= 32:
        raise ValueError('provide_one_to_32_source_clips')
    ids=set()
    for case in cases:
        if not isinstance(case.get('id'),str) or not case['id'] or case['id'] in ids:
            raise ValueError('unique_case_ids_required')
        ids.add(case['id'])
        source=Path(case['audio'])
        source=source if source.is_absolute() else path.parent/source
        if not source.is_file() or sha(source) != case['sha256']:
            raise ValueError('source_clip_missing_or_changed')
        if not isinstance(case.get('reference_text'),str) or not case.get('provenance',{}).get('review_status'):
            raise ValueError('reference_text_and_review_provenance_required')
        case['audio']=str(source.resolve())
    return cases


def run(args):
    from fastapi.testclient import TestClient
    from filelock import FileLock
    from services.api import config
    from services.api.audio import atomic_write, sha
    from services.api.db import transaction
    from services.api.main import app
    from services.api.pcm import Reader
    from services.api.provenance import runtime_identity
    from services.worker.supervisor import run_stage
    from scripts.audio_metrics import score, tokens
    from scripts.codeswitch_metrics import score_codeswitch

    references=validate_cases(args.cases.resolve())
    run_dir=args.output_root.resolve()/(args.engine+'-'+str(time.time_ns()))
    config.DATA=run_dir
    os.environ['MOM_DATA']=str(run_dir)
    before=network_probe()
    implementation=runtime_identity()
    with TestClient(app) as client:
        setup=client.post('/api/v1/setup',json={'name':'local-benchmark','password':secrets.token_urlsafe(24)})
        setup.raise_for_status()
        client.headers['x-csrf-token']=setup.json()['csrf']
        response=client.post('/api/v1/meetings',json={'title':'Speech benchmark; not a reviewed meeting','date':None,'timezone':''})
        response.raise_for_status()
        meeting=response.json()
        base='/api/v1/meetings/'+meeting['id']
        cases=[]
        for reference in references:
            with open(reference['audio'],'rb') as source:
                upload=client.post(base+'/uploads',files={'file':(Path(reference['audio']).name,source,'application/octet-stream')})
            upload.raise_for_status()
            asset_id=upload.json()['id']
            with transaction() as connection:
                asset=dict(connection.execute('SELECT * FROM assets WHERE id=?',(asset_id,)).fetchone())
            with Reader(Path(asset['path'])) as reader:
                frames=reader.getnframes()
            if not 0 < frames <= 60*16000:
                raise ValueError('benchmark_clip_requires_up_to_60_seconds; split_by_source_without_truncation')
            cases.append({'id':reference['id'],'audio':asset['path'],'canonical_audio_hash':sha(asset['path']),
                          'speech_window':{'start':0,'end':frames}})
        queued=client.post(base+'/jobs',json={'asset_id':asset_id,'device':'cuda'})
        queued.raise_for_status()
        with transaction() as connection:
            job=dict(connection.execute('SELECT * FROM jobs WHERE id=?',(queued.json()['id'],)).fetchone())
        spec={'config':json.loads(job['config']),'benchmark_cases':cases,'benchmark_precision':args.precision}
        if args.engine == 'qwen_asr':
            spec['config']['inference']['qwen_asr'].update(backend=args.qwen_backend,runtime_prefix=args.runtime_prefix)
        if args.engine == 'vibevoice':
            spec['config']['inference']['vibevoice'].update(runtime_prefix=args.runtime_prefix)
            if args.max_new_tokens is not None:
                spec['config']['inference']['vibevoice']['max_new_tokens'] = args.max_new_tokens
        if args.engine == 'parakeet' or (args.engine == 'qwen_asr' and args.qwen_backend == 'native'):
            spec['config']['inference']['optional']['runtime_prefix']=args.runtime_prefix
        started=time.monotonic()
        with FileLock(str(Path(tempfile.gettempdir())/'secure-mom-gpu.lock'),timeout=1):
            output=run_stage(job,args.engine,spec)
        results=[]
        for reference, observed in zip(references,output['cases'],strict=True):
            if reference['id'] != observed['id']:
                raise ValueError('benchmark_case_identity_mismatch')
            hypothesis=observed['result']
            if hypothesis is None:
                measured={'wer':None,'status':'FAILED_OUTPUT','failure':observed['failure'],
                          'reference_word_count':len(tokens(reference['reference_text']))}
            elif not reference['reference_text'].strip():
                measured={'wer':None,'status':'NOT_MEASURED_NO_REFERENCE'}
            elif 'reference_languages' in reference:
                measured=score_codeswitch(reference['reference_text'],hypothesis['text'],reference['reference_languages'],
                    minority_language=reference['minority_language'],critical_spans=reference.get('critical_spans',[]))
            else:
                measured=score(reference['reference_text'],hypothesis['text'],reference.get('critical_spans',[]))
            results.append({'id':reference['id'],'reference_provenance_as_supplied':reference['provenance'],
                            'reference_language':reference.get('language'),'metrics':measured,'observed':hypothesis})
        if implementation != runtime_identity():
            raise RuntimeError('implementation_changed_during_benchmark')
        report={'engine':args.engine,'scope':'Provided reference annotations; synthetic/native/regional scope must follow their provenance',
                'implementation':implementation,'input_manifest_sha256':sha(args.cases),'elapsed_seconds':time.monotonic()-started,
                'network_before':before,'network_after':network_probe(),'cases':results,
                'failed_output_cases':sum(item['observed'] is None for item in results),
                'accuracy_limits':'No medical/Moldovan/code-switch/DER claim from monolingual or synthetic clips'}
        atomic_write(run_dir/'report.json',json.dumps(report,ensure_ascii=False,indent=2).encode())
        with transaction() as connection:
            assert all(connection.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] == 0
                       for table in ('segments','candidates','accepted_events','snapshots','outbox'))
            connection.execute("UPDATE jobs SET state='complete' WHERE id=?",(job['id'],))
        print(json.dumps({'report':str(run_dir/'report.json'),'engine':args.engine,
                          'scores':[{'id':item['id'],'wer':item['metrics']['wer']} for item in results]}))
        if report['failed_output_cases']:
            raise SystemExit(1)  # A completed evaluation is not a passing model qualification.


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=Path,required=True)
    parser.add_argument('--engine',choices=['whisper','parakeet','qwen_asr','vibevoice'],required=True)
    parser.add_argument('--runtime-prefix',default='')
    parser.add_argument('--qwen-backend',choices=['native','official'],default='official')
    parser.add_argument('--max-new-tokens',type=int,default=None,help='VibeVoice diagnostic output cap, validated by job settings')
    parser.add_argument('--precision',choices=['float16','int8_float16'],default='float16',help='Whisper compute precision')
    parser.add_argument('--output-root',type=Path,default=Path('.runtime/speech-benchmarks'))
    parser.add_argument('--inside',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if sys.platform != 'linux':
        parser.error('Use the prepared Linux/WSL environment; this benchmark requires enforced network isolation')
    namespace=os.readlink('/proc/self/ns/net')
    if not args.inside:
        raise SystemExit(subprocess.call(['unshare','-Urn',sys.executable,'-m','scripts.benchmark_speech',*sys.argv[1:],'--inside'],
            env={**os.environ,'MOM_BENCHMARK_PARENT_NETNS':namespace}))
    if os.environ.get('MOM_BENCHMARK_PARENT_NETNS') in (None,namespace):
        raise RuntimeError('benchmark_requires_separate_network_namespace')
    run(args)


if __name__ == '__main__':
    main()
