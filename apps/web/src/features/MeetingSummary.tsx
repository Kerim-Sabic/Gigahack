import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import { tr } from '../translations';
import { errorMessage } from '../errors';

type SummaryState = {
 summary: null | {stale:boolean; body:{points:{text:string;source_ids:string[]}[]}};
 job: null | {id:string;state:string;error?:string}; has_transcript:boolean;
};
export function MeetingSummary({meetingId,revision,device,disabled,readOnly,act,showSource}:{
 meetingId:string;revision:number;device:string;disabled:boolean;readOnly:boolean;
 act:(fn:()=>Promise<unknown>)=>Promise<void>;showSource:(id:string)=>void;
}) {
 const result=useQuery({queryKey:['meeting-summary',meetingId,revision],queryFn:()=>api<SummaryState>(`/meetings/${meetingId}/summary`),refetchInterval:query=>query.state.data?.job&&['queued','running'].includes(query.state.data.job.state)?2000:false});
 const data=result.data,working=!!data?.job&&['queued','running'].includes(data.job.state);
 return <section className="meeting-summary">
  <div className="pageheading"><div><h2>{tr('Meeting summary')}</h2><p>{tr('A local AI overview of the saved transcript. Review it before approving minutes.')}</p></div>
   {!readOnly&&<button disabled={disabled||working||!data?.has_transcript||result.isError} onClick={()=>void act(()=>api(`/meetings/${meetingId}/summary`,'POST',{revision,device}))}>{tr(working?'Summarizing…':data?.summary?'Regenerate summary':'Generate summary')}</button>}
  </div>
  {result.isError&&<p role="alert">{errorMessage(result.error instanceof Error?result.error.message:'Unable to load summary')}</p>}
  {working&&<p role="status">{tr('Reading the transcript and summarizing the meeting locally…')}</p>}
  {data?.job?.state==='failed'&&<p role="alert" className="error">{errorMessage(data.job.error||'Summary generation failed. Try again.')}</p>}
  {data?.summary?.stale&&<p className="notice">{tr('The transcript or meeting details changed. Regenerate the summary before creating minutes.')}</p>}
  {data?.summary?<><p className="caption">{tr('AI draft · check against the source')}</p><ul className="summary-points">{data.summary.body.points.map((point,index)=><li key={index}><p>{point.text}</p><div className="summary-sources">{point.source_ids.map((id,n)=><button key={id} className="secondary" onClick={()=>showSource(id)}>{tr('Source')} {n+1}</button>)}</div></li>)}</ul></>:!working&&<p className="caption">{tr(data?.has_transcript?'Generate a summary to include the main discussion in your minutes.':'Add a transcript to generate a meeting summary.')}</p>}
 </section>;
}
