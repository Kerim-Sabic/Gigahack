"""Measure ASR speed through the existing supervisor with an isolated benchmark DB."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import tempfile
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio',type=Path,required=True)
    parser.add_argument('--gpu',type=int,default=1)
    parser.add_argument('--dual',action='store_true')
    args=parser.parse_args()
    from services.api import config
    root=config.DATA/'speed-benchmarks'/str(time.time_ns())
    config.DATA=root
    os.environ['MOM_DATA']=str(root)
    from fastapi.testclient import TestClient
    from filelock import FileLock
    from services.api.main import app
    from services.api.audio import sha, atomic_write
    from services.api.db import transaction
    from services.worker.supervisor import run_stage
    manifest=json.loads((config.ROOT/'manifests/models.lock.json').read_text())['whisper']
    assert sha(config.MODELS/'whisper/model.bin')==manifest['files']['model.bin']
    source=args.audio.resolve()
    reports=[]
    with TestClient(app) as client:
        signed=client.post('/api/v1/setup',json={'name':'speed-benchmark','password':secrets.token_urlsafe(24)})
        signed.raise_for_status()
        client.headers['x-csrf-token']=signed.json()['csrf']
        meeting=client.post('/api/v1/meetings',json={'title':'Isolated speed benchmark','date':None,'timezone':''}).json()
        base='/api/v1/meetings/'+meeting['id']
        with source.open('rb') as f:
            uploaded=client.post(base+'/uploads',files={'file':(source.name,f,'audio/mp4')})
        uploaded.raise_for_status()
        asset=uploaded.json()['id']
        with FileLock(str(Path(tempfile.gettempdir())/'secure-mom-gpu.lock'),timeout=5):
            for precision,batch,gpu in [('float16',8,args.gpu),('float16',32,args.gpu),('int8_float16',32,args.gpu)]+([('float16',16,-1)] if args.dual else []):
                queued=client.post(base+'/jobs',json={'asset_id':asset,'device':'cuda'})
                queued.raise_for_status()
                with transaction() as c:
                    job=dict(c.execute('SELECT * FROM jobs WHERE id=?',(queued.json()['id'],)).fetchone())
                options={'gpu':gpu,'precision':precision,'batch_size':batch}
                spec={'config':json.loads(job['config']),'audio':str(source),'input_sha256':sha(source),'speed_benchmark':options}
                # Unique spec/job cache identity includes profile; each profile gets one fresh stage.
                spec['benchmark_nonce']=secrets.token_hex(8)
                print('Running '+str(options),flush=True)
                result=run_stage(job,'whisper',spec)
                receipt=json.loads((root/'jobs'/job['id']/'whisper-receipt.json').read_text())
                archive = root / 'profiles' / f'{gpu}-{precision}-{batch}'
                shutil.copytree(root / 'jobs' / job['id'], archive)
                reports.append({'job_id':job['id'],'result':result,'resources':receipt['resources']})
                with transaction() as c:
                    c.execute("UPDATE jobs SET state='complete' WHERE id=?",(job['id'],))
                print(json.dumps({'profile':options,'runs':result['runs'],'cold_core_seconds':result['cold_core_seconds']}),flush=True)
        report={'input_name':source.name,'input_sha256':sha(source),'model':manifest,'profiles':reports,
                'scope':'Transcription-only speed experiment; no application transcript changes, no extraction or delivery.'}
        atomic_write(root/'report.json',json.dumps(report,ensure_ascii=False,indent=2).encode())
        print('REPORT '+str(root/'report.json'),flush=True)


if __name__=='__main__':
    main()
