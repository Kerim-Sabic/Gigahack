import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import '@fontsource/noto-sans/latin.css';
import '@fontsource/noto-sans/latin-ext.css';
import '@fontsource/noto-sans/cyrillic.css';
import './style.css';
import { api, setCsrf } from './api';
import { strings, type Lang, type Labels } from './i18n';
import { Meetings } from './features/Meetings';
import { Workspace } from './features/Workspace';

const cache=new QueryClient({defaultOptions:{queries:{retry:false,refetchOnWindowFocus:false}}});

function App(){
 const [lang,setLang]=useState<Lang>('en'),[page,setPage]=useState('meetings'),[meeting,setMeeting]=useState<string|null>(new URLSearchParams(location.search).get('meeting'));
 const t=strings[lang];
 const me=useQuery({queryKey:['me'],queryFn:async()=>{const u=await api('/me');setCsrf(u.csrf);setLang(u.language);return u;}});
 const setup=useQuery({queryKey:['setup'],queryFn:()=>api('/setup')});
 function open(id:string|null){setMeeting(id);history.replaceState({},'',id?'?meeting='+id:location.pathname);}
 if(me.isPending||setup.isPending)return <p role="status">{t.loading}</p>;
 if(!me.data)return <Login t={t} setup={!!setup.data?.required} done={()=>cache.invalidateQueries()}/>;
 return <div className="shell"><a className="skip" href="#content">Skip to content</a><aside className="sidebar"><div className="brand"><span className="brandmark">M</span><span>Secure MOM<small>MEETING WORKSPACE</small></span></div><nav>{(['meetings','actions','templates','settings'] as const).map((p,i)=><button className={page===p?'active':''} onClick={()=>{setPage(p);open(null);}} key={p}><span aria-hidden>{['▤','✓','▧','⚙'][i]}</span>{t[p]}</button>)}</nav><div className="sidebarfoot"><span className="dot"/>{t.local}<p>Evidence before approval.<br/>Your recordings stay local.</p></div></aside><div className="main"><header><span>MEETING OPERATIONS</span><div className="toolbar"><label className="sr-only" htmlFor="language">Interface language</label><select id="language" value={lang} onChange={e=>{const l=e.target.value as Lang;setLang(l);document.documentElement.lang=l;void api('/me','PATCH',{language:l});}}><option value="en">English</option><option value="ro">Română</option><option value="ru">Русский</option></select><button className="textbutton" onClick={async()=>{await api('/sessions/current','DELETE');cache.clear();location.reload();}}>{t.logout}</button></div></header><main id="content">{page==='meetings'?(meeting?<Workspace id={meeting} t={t} back={()=>open(null)}/>:<Meetings t={t} open={id=>open(id)}/>):<Other page={page} t={t}/>}</main></div></div>;
}

function Login({t,setup,done}:{t:Labels;setup:boolean;done:()=>void}){const [error,setError]=useState(''),[busy,setBusy]=useState(false);return <div className="login"><div className="brand"><span className="brandmark">M</span>Secure MOM</div><p className="eyebrow">PRIVATE MEETING WORKSPACE</p><h1>{setup?t.setup:t.login}</h1><p>No default password. Your account is stored on this computer.</p><form onSubmit={async e=>{e.preventDefault();setBusy(true);const f=new FormData(e.currentTarget);try{const u=await api(setup?'/setup':'/sessions','POST',{name:f.get('name'),password:f.get('password')});setCsrf(u.csrf);done();}catch(e){setError(String(e));}finally{setBusy(false);}}}><label>{t.username}<input name="name" autoComplete="username" required minLength={3}/></label><label>{t.password}<input name="password" type="password" autoComplete={setup?'new-password':'current-password'} required minLength={12}/></label>{error&&<p role="alert" className="error">{error}</p>}<button disabled={busy}>{busy?t.loading:t.continue} →</button></form><p className="caption">Prepare local models before processing. Setup never downloads assets.</p></div>;}

function Other({page,t}:{page:string;t:Labels}){const q=useQuery({queryKey:[page],queryFn:()=>api(page==='actions'?'/actions':'/system/proof')});return <><p className="eyebrow">WORKSPACE</p><h1>{t[page as keyof Labels]}</h1>{q.isPending?<p>{t.loading}</p>:q.isError?<p role="alert">{String(q.error)}</p>:page==='actions'?<section className="card">{q.data.length?q.data.map((i:any)=><article className="segment" key={i.meeting_id+i.subject}><div><h3>{i.text}</h3><p>{i.owner||t.notSpecified} · {i.due||t.notSpecified} · {i.status}</p>{i.condition&&<p>{i.condition}</p>}</div></article>):<p>No reviewed actions yet.</p>}</section>:page==='templates'?<section className="card"><h2>Evidence-first minutes</h2><p>Administrative, Executive and Medical meetings use a deterministic document: participants, decisions, actions, conditions, unresolved matters and amendment history.</p><p>Output language is chosen separately for each meeting. Original speech remains unchanged.</p></section>:<section className="card"><h2>Local processing status</h2><dl>{Object.entries(q.data).map(([key,value])=><React.Fragment key={key}><dt>{key.replaceAll('_',' ')}</dt><dd>{typeof value==='object'?JSON.stringify(value):String(value)}</dd></React.Fragment>)}</dl><p className="notice">Network observation is not measured. Local inference is not proof of host-wide isolation.</p><a href="http://127.0.0.1:8025" target="_blank" rel="noreferrer">Open local Mailpit inbox ↗</a></section>}</>;}

createRoot(document.getElementById('root')!).render(<QueryClientProvider client={cache}><App/></QueryClientProvider>);
