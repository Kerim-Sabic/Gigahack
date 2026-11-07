import json
import pytest
from services.worker.meeting_summary import generate_summary
from services.worker.settings import load_settings
from services.api.progress import ProgressReporter

class Response:
    def __init__(self, data): self.data = data
    def json(self): return self.data
    def raise_for_status(self): pass

class Tokenizer:
    def post(self, path, json):
        return Response({'tokens': list(range(len(json['content'])//3))})

def test_long_utterances_and_last_turn_are_read_and_checkpointed(tmp_path):
    seen=[]
    def complete(client,payload,*args):
        content=json.loads(payload['messages'][1]['content'])
        seen.extend(content['new_transcript'])
        point={'text':'Draft from source','source_ids':[content['new_transcript'][-1]['id']]}
        return Response({'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'points':[point]})}}]})
    text='Long original source. '*300
    spec={'run_dir':str(tmp_path),'config':{},'meeting':{'language':'ro'},'segments':[
        {'id':'a','text':text},{'id':'b','text':'Final unresolved proposal.'}]}
    args=(Tokenizer(),spec,load_settings().llm,tmp_path/'raw.jsonl',ProgressReporter(tmp_path,'extract'),complete)
    result=generate_summary(*args)
    assert ''.join(s['text'] for s in seen if s['id']=='a')==text
    assert seen[-1]['text']=='Final unresolved proposal.'
    assert result['points'][0]['source_ids']==['b']
    seen.clear()
    assert generate_summary(*args)==result and not seen

@pytest.mark.parametrize('finish,source,error',[('length','s','incomplete'),('stop','invented','invalid_source')])
def test_truncated_and_uncited_summary_never_published(tmp_path,finish,source,error):
    def complete(*args):
        return Response({'choices':[{'finish_reason':finish,'message':{'content':json.dumps({'points':[{'text':'Draft','source_ids':[source]}]})}}]})
    spec={'run_dir':str(tmp_path),'config':{},'meeting':{'language':'ro'},'segments':[{'id':'s','text':'Discussion'}]}
    with pytest.raises(RuntimeError,match=error):
        generate_summary(Tokenizer(),spec,load_settings().llm,tmp_path/'raw',ProgressReporter(tmp_path,'extract'),complete)
