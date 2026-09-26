import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, type Meeting } from '../api';
import { tr } from '../translations';

export function MeetingDetails({meeting:m,role,busy,act,back}:{meeting:Meeting;role:string;busy:boolean;act:(fn:()=>Promise<unknown>)=>void;back:()=>void}) {
  const accounts=useQuery({queryKey:['accounts'],queryFn:()=>api<any[]>('/accounts'),enabled:role==='admin'});
  const [confirmation,setConfirmation]=useState('');
  const processing=m.jobs?.some(job=>['queued','running'].includes(job.state));
  if(role==='viewer')return null;
  return <details className="card"><summary>{tr('Meeting details and access')}</summary>
    {processing&&<p className="notice">{tr('Cancel or finish processing before changing meeting details.')}</p>}
    <form key={m.revision} onSubmit={e=>{
      e.preventDefault();const f=new FormData(e.currentTarget);
      act(()=>api(`/meetings/${m.id}`,'PATCH',{revision:m.revision,title:f.get('title'),date:f.get('date')||null,time:f.get('time'),notes:f.get('notes'),timezone:f.get('timezone'),language:f.get('language'),classification:f.get('classification'),participants:String(f.get('participants')).split('\n').map(s=>s.trim()).filter(Boolean)}));
    }}>
      <fieldset disabled={busy||processing}>
        <label>{tr('Title')}<input name="title" defaultValue={m.title} required maxLength={200}/></label>
        <div className="formrow"><label>{tr('Date')}<input name="date" type="date" defaultValue={m.date}/></label><label>{tr('Timezone')}<input name="timezone" defaultValue={m.timezone}/></label></div>
        <label>{tr("Time")}<input name="time" type="time" defaultValue={m.time}/></label><label>{tr("Meeting notes · draft")}<textarea name="notes" defaultValue={m.notes} rows={8} maxLength={20000}/></label>
        <p className="caption">{tr("Leave date and timezone blank if unknown. Relative dates will need review.")}</p>
        <div className="formrow"><label>{tr('Minutes language')}<select name="language" defaultValue={m.language}><option value="en">English</option><option value="ro">Română</option><option value="ru">Русский</option></select></label><label>{tr('Classification')}<select name="classification" defaultValue={m.classification}>{['Administrative','Executive','Medical'].map(v=><option key={v} value={v}>{tr(v)}</option>)}</select></label></div>
        <label>{tr('Participants, one per line')}<textarea name="participants" defaultValue={m.participants?.map(p=>p.name).join('\n')} rows={3}/></label>
        <p className="caption">{tr('Changing the date or timezone requires another review. Previous approved versions remain in history.')}</p>
        <button>{tr('Save meeting details')}</button>
      </fieldset>
    </form>
    {role==='admin'&&<>
      <form onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);act(()=>api(`/meetings/${m.id}/members`,'POST',{user_id:f.get('account')}));}}>
        <h3>{tr('Grant meeting access')}</h3>
        {accounts.isError?<p role="alert">{String(accounts.error)}</p>:<label>{tr('Local account')}<select name="account" required aria-label={tr('Local account')}><option value="">{tr('Choose an account')}</option>{accounts.data?.map(a=><option key={a.id} value={a.id}>{a.name} · {tr(a.role)}</option>)}</select></label>}
        <p className="caption">{tr('Admin role does not grant access to other people\'s meetings.')}</p>
        <button disabled={busy||!accounts.data?.length}>{tr('Grant access')}</button>
      </form>
      <details><summary>{tr('Delete this meeting')}</summary><p className="notice">{tr('Deletes recordings, transcripts, reviews and exports. This cannot be undone. Type the exact meeting title to confirm.')}</p>
        <label>{tr('Confirm meeting title')}<input value={confirmation} onChange={e=>setConfirmation(e.target.value)} autoComplete="off"/></label>
        <button className="secondary" disabled={busy||processing||confirmation!==m.title} onClick={()=>act(async()=>{await api(`/meetings/${m.id}`,'DELETE',{revision:m.revision,confirm_title:confirmation});back();})}>{tr('Delete this meeting')}</button>
      </details>
    </>}
  </details>;
}

export function CandidateHistory({id}:{id:string|undefined}) {
  const history=useQuery({queryKey:['candidate-history',id],queryFn:()=>api<any[]>(`/items/${id}/history`),enabled:!!id,refetchInterval:4000});
  return <><h3>{tr('Decision history')}</h3>{history.isError?<p role="alert">{String(history.error)}</p>:history.data?.map(row=>{
    const body=JSON.parse(row.body),amendment=body.human_amendment;
    return <article key={row.id}><p><strong>{tr(body.kind)}</strong> · {tr(row.review.replaceAll('_',' '))}</p><p>{body.text}</p>
      <p>{body.owner||'—'} · {body.due||'—'}</p>{body.condition&&<p>{body.condition}</p>}{body.value&&<p>{body.value}</p>}
      {amendment&&<details><summary>{tr('Secretary amendment')}</summary><p>{amendment.reason}</p><p>{tr('Changed fields')}: {amendment.fields.map(tr).join(', ')}</p><p>{tr('Reviewer')}: {amendment.actor}</p><time dateTime={new Date(amendment.created*1000).toISOString()}>{new Date(amendment.created*1000).toLocaleString()}</time>{amendment.resolved_issues?.map((issue:string)=><p key={issue}>{issue}</p>)}</details>}
    </article>;
  })}</>;
}
