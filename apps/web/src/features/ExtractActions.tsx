import {useState} from 'react';
import {Sparkles} from 'lucide-react';
import {api,type Meeting} from '../api';
import {tr} from '../translations';

export function ExtractActions({meetingId,assetId,device,disabled,hasTranscript,jobs,onResult,act}:{meetingId:string;assetId?:string;device:string;disabled:boolean;hasTranscript:boolean;jobs:Meeting['jobs'];onResult:()=>void;act:(fn:()=>Promise<unknown>)=>Promise<void>}){
 const [notice,setNotice]=useState(''),[jobId,setJobId]=useState('');
 const job=jobs?.find(j=>j.id===jobId);
 function extract(){setNotice('');void act(async()=>{
  const job=await api<{id:string;state:string}>(`/meetings/${meetingId}/jobs`,'POST',{asset_id:assetId,device,transcript_only:true});
  if(['failed','cancelled'].includes(job.state))await api(`/jobs/${job.id}/retry`,'POST');
  setJobId(job.id);
  setNotice(tr(job.state==='complete'?'This transcript has already been analyzed. Review its actions below.':'Reading the transcript locally. Suggested actions will appear for review.'));
  onResult();
 });}
 const status=job?.state==='complete'?tr('Analysis saved. Ready for review.'):job&&['failed','cancelled'].includes(job.state)?tr('Analysis stopped. Your transcript is retained. Retry when ready.'):notice;
 return <section className="extract-actions" aria-label={tr('AI action extraction')}><div><h3>{tr('Turn this transcript into actions')}</h3><p>{tr('The local AI reads the saved text for decisions, owners and deadlines. Review suggestions before approval.')}</p>{!hasTranscript&&<small>{tr('Transcribe audio or import a transcript first.')}</small>}</div><button disabled={disabled||!hasTranscript||!assetId} onClick={extract}><Sparkles size={17} aria-hidden="true"/>{tr('Extract actions with AI')}</button>{status&&<p className="extraction-notice" role="status">{status}</p>}</section>;
}
