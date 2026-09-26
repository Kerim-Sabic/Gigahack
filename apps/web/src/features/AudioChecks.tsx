import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import { tr } from '../translations';

type Recovery = {text:string;attempt:'initial'|'short_retry';source_start:number;source_end:number};
type Observation = {kind:'speech_without_transcript'|'empty_second_recognizer';start:number;end:number;hypotheses?:Recovery[]};
type CheckPage = {asset_id:string;total:number;items:Observation[]};

export function AudioChecks({jobId,running,play}:{jobId:string;running:boolean;play:(span:{asset_id:string;start:number;end:number})=>void}) {
 const [offset,setOffset]=useState(0);
 const checks=useQuery({queryKey:['audio-checks',jobId,running,offset],queryFn:()=>api<CheckPage>(`/jobs/${jobId}/audio-checks?offset=${offset}&limit=20`),refetchInterval:running?3000:false});
 if(checks.isError)return <p role="alert">{tr('Audio checks could not be loaded.')} <button onClick={()=>void checks.refetch()}>{tr('Retry')}</button></p>;
 if(!checks.data?.total)return null;
 const page=checks.data;
 return <section className="notice" aria-label={tr('Audio passages to check')}>
  <h3>{tr('Audio passages to check')} ({page.total})</h3>
  <p>{tr('These automated flags may be wrong. Compare any recovery hypothesis with the source before correcting the transcript.')}</p>
  <p>{tr('Flags come from the latest analysis of this recording. Transcript edits do not recalculate them.')}</p>
  <ul>{page.items.map(item=><li key={`${item.kind}-${item.start}-${item.end}`}>
   <button onClick={()=>play({...item,asset_id:page.asset_id})}>{tr('Play passage')} {(item.start/16000).toFixed(1)}–{(item.end/16000).toFixed(1)}s</button>{' '}
   <span>{tr(item.kind==='speech_without_transcript'?'Possible speech outside the transcript.':'The second recognizer returned no text here.')}</span>
   {item.hypotheses?.map((hypothesis,index)=><details key={index}>
    <summary>{tr(hypothesis.attempt==='short_retry'?'Recovery hypothesis · shorter retry':'Recovery hypothesis · initial pass')}</summary>
    <p>{hypothesis.text||tr('The second recognizer returned no text here.')}</p>
    <p>{tr('This hypothesis includes surrounding context and may repeat nearby words. It has not been added to the transcript.')}</p>
    <button onClick={()=>play({asset_id:page.asset_id,start:hypothesis.source_start,end:hypothesis.source_end})}>{tr('Play recovery context')} {(hypothesis.source_start/16000).toFixed(1)}–{(hypothesis.source_end/16000).toFixed(1)}s</button>
   </details>)}
  </li>)}</ul>
  <div className="toolbar"><button disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-20))}>{tr('Previous')}</button><button disabled={offset+20>=page.total} onClick={()=>setOffset(offset+20)}>{tr('Next')}</button></div>
 </section>;
}
