import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, type Meeting } from '../api';
import type { Labels } from '../i18n';

export function Meetings({t,open}: {t:Labels;open:(id:string)=>void}) {
 const [creating,setCreating]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const query=useQuery({queryKey:['meetings'],queryFn:()=>api<Meeting[]>('/meetings')});
 const cache=useQueryClient();
 async function create(e:React.FormEvent<HTMLFormElement>) {e.preventDefault();setBusy(true);setError('');const f=new FormData(e.currentTarget);try {const m=await api<Meeting>('/meetings','POST',{title:f.get('title'),date:f.get('date'),language:f.get('language'),timezone:f.get('timezone'),classification:f.get('classification'),participants:String(f.get('participants')).split('\n').filter(Boolean)});await cache.invalidateQueries({queryKey:['meetings']});open(m.id);}catch(e){setError(String(e));}finally{setBusy(false);}}
 return <><div className="pageheading"><div><p className="eyebrow">YOUR MEETING RECORD</p><h1>{t.meetings}</h1><p>From conversation to reviewed decisions.</p></div><button onClick={()=>setCreating(!creating)}>＋ {t.new}</button></div>
 {error&&<p role="alert" className="error">{error}</p>}
 {creating&&<form className="card form" onSubmit={create}><h2>{t.new}</h2><label>{t.title}<input name="title" required maxLength={200} autoFocus/></label><div className="formrow"><label>{t.date}<input name="date" type="date" defaultValue={new Date().toISOString().slice(0,10)} required/></label><label>Timezone<input name="timezone" defaultValue="Europe/Chisinau" required/></label></div><div className="formrow"><label>Minutes language<select name="language"><option value="en">English</option><option value="ro">Română</option><option value="ru">Русский</option></select></label><label>Classification<select name="classification"><option>Administrative</option><option>Executive</option><option>Medical</option></select></label></div><label>{t.participants}<textarea name="participants" rows={3}/></label><button disabled={busy}>{busy?t.loading:t.save}</button></form>}
 {query.isPending?<p role="status">{t.loading}</p>:query.isError?<p role="alert">{String(query.error)}</p>:query.data.length===0?<section className="card empty"><span className="emptyicon">▤</span><h2>{t.empty}</h2><p>Create a meeting, add your participants, then record or upload audio.<br/>Every decision stays connected to its source.</p><button onClick={()=>setCreating(true)}>{t.new}</button></section>:<div className="meetinglist">{query.data.map(m=><button className="meetingrow" key={m.id} onClick={()=>open(m.id)}><span className="datebox">{m.date.slice(8)}<small>{m.date.slice(0,7)}</small></span><span><strong>{m.title}</strong><small>{m.classification} · {m.language.toUpperCase()}</small></span><span className="badge">{m.status.replaceAll('_',' ')}</span><span aria-hidden>→</span></button>)}</div>}
 <div className="guidance"><h3>A record you can trace</h3><p>Review the original speech, see where a decision changed, and approve an exact version before sending.</p></div></>;
}
