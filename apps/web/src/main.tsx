import brand from '../../../config/brand.json';
import { Templates } from './features/Templates';
import { tr, setUiLanguage } from './translations';
import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import '@fontsource/noto-sans/latin.css';
import '@fontsource/noto-sans/latin-ext.css';
import '@fontsource/noto-sans/cyrillic.css';
import './style.css';
import './experience.css';
import './audio-workflow.css';
import { api, setCsrf } from './api';
import { strings, type Lang, type Labels } from './i18n';
import { Meetings } from './features/Meetings';
import { Workspace } from './features/Workspace';
import { Actions } from './features/Actions';
import { Settings } from './features/Settings';

const cache=new QueryClient({defaultOptions:{queries:{retry:false,refetchOnWindowFocus:false}}});

function App(){
 const [lang,setLang]=useState<Lang>('en'),[page,setPage]=useState('meetings'),[meeting,setMeeting]=useState<string|null>(new URLSearchParams(location.search).get('meeting'));
 const [notice,setNotice]=useState('');
 const t=strings[lang];
 const me=useQuery({queryKey:['me'],queryFn:async()=>{const u=await api('/me');setCsrf(u.csrf);setLang(u.language);setUiLanguage(u.language);return u;}});
 const setup=useQuery({queryKey:['setup'],queryFn:()=>api('/setup')});
 function open(id:string|null){setMeeting(id);history.replaceState({},'',id?'?meeting='+id:location.pathname);}
 if(me.isPending||setup.isPending)return <p role="status">{t.loading}</p>;
 if(!me.data)return <Login t={t} setup={!!setup.data?.required} done={()=>cache.invalidateQueries()}/>;
 return <div className="shell"><a className="skip" href="#content">{tr("Skip to content")}</a><aside className="sidebar"><div className="brand"><img className="brandmark" src="/brand/symbol.svg" alt="" width="36" height="40"/><span>{brand.name}<small>{tr("MEETING WORKSPACE")}</small></span></div><nav>{(['meetings','actions','templates','settings'] as const).map((p,i)=><button className={page===p?'active':''} onClick={()=>{setPage(p);open(null);}} key={p}><span aria-hidden>{['▤','✓','▧','⚙'][i]}</span>{t[p]}</button>)}</nav><div className="sidebarfoot"><span className="dot"/>{t.local}<p>{tr("Evidence before approval.")}<br/>{tr("Your recordings stay local.")}</p></div></aside><div className="main"><header><span>{tr("MEETING OPERATIONS")}</span><div className="toolbar"><label className="sr-only" htmlFor="language">{tr("Interface language")}</label><select id="language" value={lang} onChange={async e=>{const l=e.target.value as Lang;try{await api('/me','PATCH',{language:l});setLang(l);setUiLanguage(l);setNotice('');}catch(error){setNotice(error instanceof Error?error.message:tr('The request failed. Check the form, refresh, and try again.'));}}}><option value="en">English</option><option value="ro">Română</option><option value="ru">Русский</option></select><button className="textbutton" onClick={async()=>{await api('/sessions/current','DELETE');cache.clear();location.reload();}}>{t.logout}</button></div></header><main id="content">{notice&&<p role="alert" className="error">{notice}</p>}{page==='meetings'?(meeting?<Workspace key={meeting} role={me.data.role} id={meeting} t={t} back={()=>open(null)}/>:<Meetings canCreate={me.data.role!=='viewer'} t={t} open={id=>open(id)}/>):page==='settings'?<Settings role={me.data.role}/>:page==='templates'?<Templates role={me.data.role}/>:<Actions/>}</main></div></div>;
}

function Login({t,setup,done}:{t:Labels;setup:boolean;done:()=>void}){const [error,setError]=useState(''),[busy,setBusy]=useState(false);return <div className="login"><div className="brand"><img className="brandmark" src="/brand/symbol.svg" alt="" width="36" height="40"/>{brand.name}</div><p className="eyebrow">{tr("PRIVATE MEETING WORKSPACE")}</p><h1>{setup?t.setup:t.login}</h1><p>{tr("No default password. Your account is stored on this computer.")}</p><form onSubmit={async e=>{e.preventDefault();setBusy(true);const f=new FormData(e.currentTarget);try{const u=await api(setup?'/setup':'/sessions','POST',{name:f.get('name'),password:f.get('password')});setCsrf(u.csrf);done();}catch(e){setError(e instanceof Error ? e.message : tr('The request failed. Check the form, refresh, and try again.'));}finally{setBusy(false);}}}><label>{t.username}<input name="name" autoComplete="username" required minLength={3}/></label><label>{t.password}<input name="password" type="password" autoComplete={setup?'new-password':'current-password'} required minLength={12}/></label>{error&&<p role="alert" className="error">{error}</p>}<button disabled={busy}>{busy?t.loading:t.continue} →</button></form><p className="caption">{tr("Prepare local models before processing. Setup never downloads assets.")}</p></div>;}

createRoot(document.getElementById('root')!).render(<QueryClientProvider client={cache}><App/></QueryClientProvider>);
