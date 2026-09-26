import {memo,useEffect,useMemo,useRef,useState,type CSSProperties} from 'react';
import {useQuery} from '@tanstack/react-query';
import {Search,MoreHorizontal,Play,Pencil,History,X,ArrowLeft,ArrowRight} from 'lucide-react';
import {api} from '../api';
import {tr} from '../translations';
import {speakerIndex,speakerInk,speakerPalette,timeLabel,type SpeechSegment} from './transcriptModel';

export async function loadTranscript(id:string,signal?:AbortSignal){
 const result:SpeechSegment[]=[];
 for(let offset=0;;offset+=200){signal?.throwIfAborted();const page=await api<SpeechSegment[]>(`/meetings/${id}/transcript?limit=200&offset=${offset}`);result.push(...page);if(page.length<200)break;}
 return result;
}
function MarkedText({text,query}:{text:string;query:string}){
 if(!query)return <>{text}</>;const parts=[];let start=0,index=text.toLocaleLowerCase().indexOf(query.toLocaleLowerCase());
 while(index>=0){parts.push(text.slice(start,index),<mark key={index}>{text.slice(index,index+query.length)}</mark>);start=index+query.length;index=text.toLocaleLowerCase().indexOf(query.toLocaleLowerCase(),start);}parts.push(text.slice(start));return <>{parts}</>;
}
export function TranscriptExperience({segments,activeId,jumpId,readOnly,seek,save,busy}:{jumpId?:string;segments:SpeechSegment[];activeId?:string;readOnly:boolean;seek:(s:SpeechSegment)=>void;save:(s:SpeechSegment,text:string,speaker:string|null)=>Promise<void>;busy:boolean}){
 const [search,setSearch]=useState(''),[page,setPage]=useState(0),[follow,setFollow]=useState(false);
 const filtered=useMemo(()=>segments.filter(s=>!search||s.text.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase())),[segments,search]);
 const pages=Math.ceil(filtered.length/80),safePage=Math.min(page,Math.max(0,pages-1)),visible=filtered.slice(safePage*80,(safePage+1)*80);
 useEffect(()=>{if(jumpId){setSearch('');const index=segments.findIndex(s=>s.id===jumpId);if(index>=0)setPage(Math.floor(index/80));}},[jumpId,segments]);
 useEffect(()=>{if(jumpId)document.getElementById('utterance-'+jumpId)?.scrollIntoView({block:'center',behavior:'smooth'});},[jumpId,safePage]);
 const speakers=useMemo(()=>Array.from(new Set(segments.map(s=>s.speaker).filter((s):s is string=>!!s))),[segments]);
 useEffect(()=>{if(follow&&activeId&&!search){const index=segments.findIndex(s=>s.id===activeId);if(index>=0)setPage(Math.floor(index/80));}},[follow,activeId,segments,search]);
 useEffect(()=>{if(follow&&activeId&&!search)document.getElementById('utterance-'+activeId)?.scrollIntoView({block:'center',behavior:'smooth'});},[follow,activeId,safePage,search]);
 return <section className="transcript-document" aria-label={tr('Transcript')}><div className="transcript-tools"><div className="transcript-search"><Search size={17}/><input aria-label={tr('Search transcript')} placeholder={tr('Search transcript')} value={search} onChange={e=>{setSearch(e.target.value);setPage(0);}}/>{search&&<button className="icon-button" aria-label={tr('Clear search')} onClick={()=>setSearch('')}><X size={15}/></button>}</div><label className="follow-control"><input type="checkbox" checked={follow} onChange={e=>setFollow(e.target.checked)}/>{tr('Follow audio')}</label></div>
 {search&&<p className="search-count" role="status">{filtered.length} {tr('matching passages')}</p>}
 <div className="conversation">{visible.map(s=><Utterance key={s.id} segment={s} active={s.id===activeId} query={search.trim()} readOnly={readOnly} seek={seek} save={save} speakers={speakers} busy={busy}/>)}</div>
 {!filtered.length&&<p className="empty-transcript">{tr(search?'No matching passages.':'No transcript available.')}</p>}
 {pages>1&&<nav className="transcript-pagination" aria-label={tr('Transcript navigation')}><button className="textbutton" disabled={!safePage} onClick={()=>setPage(safePage-1)}><ArrowLeft size={16}/>{tr('Earlier conversation')}</button><span>{safePage+1} / {pages}</span><button className="textbutton" disabled={safePage+1>=pages} onClick={()=>setPage(safePage+1)}>{tr('Continue reading')}<ArrowRight size={16}/></button></nav>}</section>;
}
const Utterance=memo(function Utterance({segment:s,active,query,readOnly,seek,save,speakers,busy}:{segment:SpeechSegment;active:boolean;query:string;readOnly:boolean;seek:(s:SpeechSegment)=>void;save:(s:SpeechSegment,text:string,speaker:string|null)=>Promise<void>;speakers:string[];busy:boolean}){
 const [editing,setEditing]=useState(false),[text,setText]=useState(s.text),[speaker,setSpeaker]=useState(s.speaker||''),[history,setHistory]=useState(false),[error,setError]=useState('');
 const menu=useRef<HTMLDetailsElement>(null),editor=useRef<HTMLTextAreaElement>(null),index=speakerIndex(s.speaker);
 const revisions=useQuery({queryKey:['segment-history',s.id,s.revision],queryFn:()=>api<any[]>(`/segments/${s.id}/history`),enabled:history});
 const raw=useMemo(()=>JSON.parse(s.raw||'{}'),[s.raw]),alternatives=useMemo(()=>JSON.parse(s.alternatives||'[]'),[s.alternatives]);
 const begin=()=>{setText(s.text);setSpeaker(s.speaker||'');setError('');setEditing(true);if(menu.current)menu.current.open=false;};
 const commit=async()=>{if(!text.trim()||busy)return;try{await save(s,text,speaker.trim()||null);setEditing(false);}catch(e){setError(String(e));}};
 useEffect(()=>{if(editing)editor.current?.focus();},[editing]);
 return <article id={'utterance-'+s.id} className={`utterance ${active?'is-active':''}`} style={{'--speaker':speakerPalette[index],'--speaker-ink':speakerInk[index]} as CSSProperties} aria-current={active?'true':undefined}>
 <div className="speaker-line"><span className="speaker-dot"/><span className="speaker-name">{s.speaker||tr('Unknown speaker')}</span><button className="utterance-time" aria-label={`${tr('Play from')} ${timeLabel(s.start/16000)}`} onClick={()=>seek(s)}>{timeLabel(s.start/16000)}</button></div>
 {!editing&&<div className="utterance-controls"><button className="icon-button" aria-label={tr('Play passage')} onClick={()=>seek(s)}><Play size={15}/></button>{!readOnly&&<button className="icon-button" aria-label={tr('Edit transcript')} onClick={begin}><Pencil size={15}/></button>}<details className="utterance-menu" ref={menu}><summary aria-label={tr('Passage options')}><MoreHorizontal size={18}/></summary><div className="context-menu">{!readOnly&&<button onClick={begin}><Pencil size={14}/>{tr('Edit transcript / speaker')}</button>}<button onClick={()=>{setHistory(!history);if(menu.current)menu.current.open=false;}}><History size={14}/>{tr('History & source')}</button></div></details></div>}
 {editing?<div className="utterance-editor" onKeyDown={e=>{if(e.key==='Escape'){setEditing(false);e.stopPropagation();}if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();void commit();}}}><textarea ref={editor} aria-label={tr('Transcript text')} value={text} onChange={e=>setText(e.target.value)} maxLength={10000} rows={Math.max(3,Math.min(10,Math.ceil(text.length/85)))}/><div className="edit-footer"><label>{tr('Speaker')}<input aria-label={tr('Speaker')} list={'speakers-'+s.id} value={speaker} maxLength={200} onChange={e=>setSpeaker(e.target.value)}/></label><datalist id={'speakers-'+s.id}>{speakers.map(name=><option key={name} value={name}/>)}</datalist><div><button className="textbutton" onClick={()=>setEditing(false)} disabled={busy}>{tr('Cancel')}</button><button onClick={()=>void commit()} disabled={busy||!text.trim()}>{tr('Save')}</button></div></div>{error&&<p role="alert" className="error">{error}</p>}</div>:<p className="utterance-text" onClick={()=>seek(s)}><MarkedText text={s.text} query={query}/></p>}
 {history&&<div className="source-history"><div className="toolbar"><strong>{tr('History & source')}</strong><button className="icon-button" aria-label={tr('Close history')} onClick={()=>setHistory(false)}><X size={16}/></button></div><p>{tr('Revision')} {s.revision} · {tr(raw.origin==='user_supplied_transcript'?'Imported transcript · approximate timestamps':'Original transcript')}</p>{raw.boundary_review&&<p>{tr('Check this passage against the audio.')}</p>}{raw.supplied_language_labels?.length>0&&<p>{tr('Unverified language labels')}: {raw.supplied_language_labels.join(', ')}</p>}{revisions.isError&&<p role="alert">{String(revisions.error)}</p>}{revisions.data?.map(r=><div key={r.revision}><small>{tr('Revision')} {r.revision}</small><p>{r.text}</p></div>)}{revisions.data?.length===0&&<small>{tr('No earlier revisions.')}</small>}{alternatives.map((a:any,i:number)=><details key={i}><summary>{tr('Alternative hypothesis · ')}{a.engine}</summary><p>{a.text||tr('The second recognizer returned no text here.')}</p></details>)}</div>}
 </article>;
});
