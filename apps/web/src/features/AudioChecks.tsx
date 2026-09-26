import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import { tr } from '../translations';

type Recovery = {text:string;attempt:'initial'|'short_retry';source_start:number;source_end:number};
type Observation = {kind:'speech_without_transcript'|'empty_second_recognizer';start:number;end:number;hypotheses?:Recovery[];inserted_segment_id?:string|null};
type CheckPage = {asset_id:string;total:number;items:Observation[]};

export function AudioChecks({jobId,running,play,revision,readOnly=true,disabled=false}:{jobId:string;running:boolean;play:(span:{asset_id:string;start:number;end:number})=>void;revision?:number;readOnly?:boolean;disabled?:boolean}) {
 const [offset,setOffset]=useState(0),[saving,setSaving]=useState(false),[error,setError]=useState('');
 const cache=useQueryClient();
 const checks=useQuery({queryKey:['audio-checks',jobId,running,offset],queryFn:()=>api<CheckPage>(`/jobs/${jobId}/audio-checks?offset=${offset}&limit=20`),refetchInterval:running?3000:false});
 if(checks.isError)return <p role="alert">{tr('Audio checks could not be loaded.')} <button onClick={()=>void checks.refetch()}>{tr('Retry')}</button></p>;
 if(!checks.data?.total)return null;
 const page=checks.data;
 return <section className="notice" aria-label={tr('Audio passages to check')}>
  <h3>{tr('Audio passages to check')} ({page.total})</h3>
  <p>{tr('These automated flags may be wrong. Compare any recovery hypothesis with the source before correcting the transcript.')}</p>
  <p>{tr('Flags come from the latest analysis of this recording. Transcript edits do not recalculate them.')}</p>
  {error&&<p role="alert">{error}</p>}
  <ul>{page.items.map(item=><li key={`${item.kind}-${item.start}-${item.end}`}>
   <button onClick={()=>play({...item,asset_id:page.asset_id})}>{tr('Play passage')} {(item.start/16000).toFixed(1)}–{(item.end/16000).toFixed(1)}s</button>{' '}
   <span>{tr(item.kind==='speech_without_transcript'?'Possible speech outside the transcript.':'The second recognizer returned no text here.')}</span>
   {item.hypotheses?.map((hypothesis,index)=><details key={index}>
    <summary>{tr(hypothesis.attempt==='short_retry'?'Recovery hypothesis · shorter retry':'Recovery hypothesis · initial pass')}</summary>
    <p>{hypothesis.text||tr('The second recognizer returned no text here.')}</p>
    <p>{tr('This hypothesis includes surrounding context and may repeat nearby words. It has not been added to the transcript.')}</p>
    <button onClick={()=>play({asset_id:page.asset_id,start:hypothesis.source_start,end:hypothesis.source_end})}>{tr('Play recovery context')} {(hypothesis.source_start/16000).toFixed(1)}–{(hypothesis.source_end/16000).toFixed(1)}s</button>
   </details>)}
   {item.inserted_segment_id?<p role="status">{tr('Reviewed words added to the transcript.')}</p>:item.kind==='speech_without_transcript'&&!readOnly&&<details>
    <summary>{tr('Add reviewed words')}</summary>
    <p>{tr('Enter only words you heard inside the flagged interval. Do not copy surrounding context. A new analysis is required before creating minutes.')}</p>
    <form onSubmit={async event=>{event.preventDefault();const form=new FormData(event.currentTarget);setSaving(true);setError('');try{await api(`/jobs/${jobId}/transcript-additions`,'POST',{revision,start:item.start,end:item.end,text:form.get('text'),speaker:form.get('speaker')||null,reason:form.get('reason'),reviewed:form.get('reviewed')==='on'});await cache.invalidateQueries();}catch(error){setError(error instanceof Error?error.message:tr('The request failed. Check the form, refresh, and try again.'));}finally{setSaving(false);}}}>
     <fieldset disabled={saving||running||disabled||revision===undefined}>
      <label>{tr('Corrected words for this interval')}<textarea name="text" required maxLength={10000}/></label>
      <label>{tr('Speaker (manual)')}<input name="speaker" maxLength={200}/></label>
      <label>{tr('Reason for correction')}<input name="reason" required minLength={3} maxLength={1000}/></label>
      <label><input name="reviewed" type="checkbox" required/>{tr('I listened to this interval and checked these words.')}</label>
      <button>{tr('Save reviewed words')}</button>
     </fieldset>
    </form>
   </details>}
  </li>)}</ul>
  <div className="toolbar"><button disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-20))}>{tr('Previous')}</button><button disabled={offset+20>=page.total} onClick={()=>setOffset(offset+20)}>{tr('Next')}</button></div>
 </section>;
}
