import {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {api} from '../api';
import {tr} from '../translations';
type Action={meeting_id:string;subject:string;text:string;owner:string|null;due:string|null;status:string;condition?:string};
export function Actions(){
 const [search,setSearch]=useState(''),[owner,setOwner]=useState('');
 const query=useQuery({queryKey:['actions'],queryFn:()=>api<Action[]>('/actions'),refetchInterval:5000});
 const meetings=useQuery({queryKey:['action-meetings'],queryFn:()=>api<{id:string;title:string}[]>('/meetings')});
 const titles=new Map(meetings.data?.map(m=>[m.id,m.title]));
 const items=(query.data||[]).filter(i=>(!owner||i.owner===owner)&&(!search||`${i.text} ${i.owner||''} ${titles.get(i.meeting_id)||''}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()))).sort((a,b)=>(a.due||'9999').localeCompare(b.due||'9999'));
 return <section className="actions-register"><p className="eyebrow">{tr('WORKSPACE')}</p><h1>{tr('Actions')}</h1><p className="caption">{tr('Reviewed actions across your meetings. Open a meeting to check evidence or update details.')}</p><div className="register-controls"><input type="search" aria-label={tr('Search actions')} placeholder={tr('Search actions')} value={search} onChange={e=>setSearch(e.target.value)}/><select aria-label={tr('Filter by owner')} value={owner} onChange={e=>setOwner(e.target.value)}><option value="">{tr('All owners')}</option>{[...new Set((query.data||[]).map(i=>i.owner).filter((s):s is string=>!!s))].sort().map(name=><option key={name}>{name}</option>)}</select></div>{query.isPending?<p role="status">{tr('Loading…')}</p>:query.isError?<p role="alert">{String(query.error)}</p>:!items.length?<p className="actions-empty">{tr(query.data?.length?'Choose another view or clear your search.':'No reviewed actions yet.')}</p>:<div className="register-list">{items.map(i=><a className="register-row" key={i.meeting_id+i.subject} href={`?meeting=${encodeURIComponent(i.meeting_id)}&view=review`}><div><small>{titles.get(i.meeting_id)||tr('Meeting')}</small><h3>{i.text}</h3>{i.condition&&<p>{i.condition}</p>}<span className="action-kind">{tr(i.status)}</span></div><div><small>{tr('Owner')}</small><strong>{i.owner||tr('Not specified')}</strong></div><div><small>{tr('Deadline')}</small><strong>{i.due||tr('Not specified')}</strong></div><span aria-hidden="true">↗</span></a>)}</div>}</section>;
}
