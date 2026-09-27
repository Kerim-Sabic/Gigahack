import {useMemo,useState,type ReactNode} from 'react';
import {Check,ChevronRight,FileText,UserRound,CalendarDays} from 'lucide-react';
import {tr} from '../translations';
import {timeLabel,type SpeechSegment} from './transcriptModel';

type Item={id:string;review:string;body:{subject:string;text:string;category:string;kind:string;owner?:string;due?:string;condition?:string;value?:string;uncertainties:string[]};evidence:{id:string;field:string;quote:string;segment_id:string;revision:number}[]};
export function ActionReview({items,segments,disabled,canAccept,readOnly,review,openSource,edit,history}:{items:Item[];segments:SpeechSegment[];disabled:boolean;canAccept:boolean;readOnly:boolean;review:(item:Item,action:'accepted'|'excluded')=>Promise<boolean>;openSource:(ref:Item['evidence'][number])=>void;edit:(item:Item,select:(id:string)=>void)=>ReactNode;history:(id:string)=>ReactNode}){
 const [selection,setSelection]=useState(''),[filter,setFilter]=useState('pending'),[search,setSearch]=useState(''),[field,setField]=useState('text');
 const pending=items.filter(i=>!['accepted','excluded'].includes(i.review));
 const visible=items.filter(i=>(filter==='all'||(filter==='pending'?!['accepted','excluded'].includes(i.review):i.review==='accepted'))&&(!search||`${i.body.text} ${i.body.subject} ${i.body.owner||''}`.toLocaleLowerCase().includes(search.toLocaleLowerCase())));
 const selected=visible.find(i=>i.id===selection)||visible[0];
 const context=useMemo(()=>{
  if(!selected)return [];
  const required=new Set(selected.evidence.map(e=>e.segment_id));
  const result=new Map<string,SpeechSegment>();
  for(const id of required){const anchor=segments.find(s=>s.id===id);if(!anchor)continue;
   const recording=segments.filter(s=>s.asset_id===anchor.asset_id),index=recording.findIndex(s=>s.id===id);
   for(const s of recording.slice(Math.max(0,index-2),index+3))result.set(s.id,s);
  }
  return [...result.values()].sort((a,b)=>a.start-b.start).slice(0,12);
 },[selected,segments]);
 const sources=selected?.evidence.filter(e=>e.field===field)||[];
 async function decide(action:'accepted'|'excluded'){
  if(!selected)return;const saved=await review(selected,action);if(!saved)return;
  setSelection(visible.find(i=>i.id!==selected.id)?.id||'');setField('text');
 }
 return <section className="action-review" aria-label={tr('Review actions')}>
  <div className="actions-heading"><div><h2>{tr('Decisions & actions')}</h2><p>{pending.length} {tr('to review')} · {items.filter(i=>i.review==='accepted').length} {tr('reviewed')}</p></div><input type="search" aria-label={tr('Find an action or decision')} placeholder={tr('Find an action or decision')} value={search} onChange={e=>setSearch(e.target.value)}/></div>
  <div className="action-filters">{[['pending','Needs review'],['accepted','Reviewed'],['all','All items']].map(([key,label])=><button className="textbutton" key={key} aria-pressed={filter===key} onClick={()=>{setFilter(key);setSelection('');setField('text');}}>{tr(label)}</button>)}</div>
  {!visible.length?<div className="actions-empty"><Check size={25} aria-hidden="true"/><h3>{tr(items.length?'No items in this view':'No actions yet')}</h3><p>{tr(items.length?'Choose another view or clear your search.':'Extract actions from the transcript using the AI button above.')}</p></div>:<div className="action-layout">
   <div className="action-queue" aria-label={tr('Action list')}>{visible.map(item=><button key={item.id} aria-pressed={selected?.id===item.id} onClick={()=>{setSelection(item.id);setField('text');}}><span className="action-kind">{tr(item.body.category)} · {tr(item.body.kind)}</span><strong>{item.body.text}</strong><span className="action-row-meta">{item.body.owner||tr('Owner not specified')}{item.body.due?' · '+item.body.due:''}</span>{item.review==='accepted'&&<Check size={14} aria-label={tr('Reviewed')}/>}</button>)}</div>
   {selected&&<article className="action-reader" key={selected.id}><div className="action-title"><span className="action-kind">{tr(selected.body.category)} · {tr(selected.body.kind)}</span><span className="caption">{tr(selected.review.replaceAll('_',' '))}</span></div><h3>{selected.body.text}</h3>
    <div className="action-assignment"><button className="source-field" onClick={()=>setField('owner')}><UserRound size={18}/><span><small>{tr('Owner')}</small><strong>{selected.body.owner||tr('Not specified')}</strong></span></button><button className="source-field" onClick={()=>setField('due')}><CalendarDays size={18}/><span><small>{tr('Deadline')}</small><strong>{selected.body.due||tr('Not specified')}</strong></span></button></div>
    {selected.body.condition&&<p><strong>{tr('Condition')}: </strong>{selected.body.condition}</p>}{selected.body.value&&<p><strong>{tr('Value')}: </strong>{selected.body.value}</p>}
    {!!selected.body.uncertainties.length&&<div className="notice"><strong>{tr('Check before accepting')}</strong>{selected.body.uncertainties.map((text,i)=><p key={i}>{text}</p>)}</div>}
    <section className="action-source"><div className="action-source-title"><FileText size={16}/><strong>{tr('Source evidence')}</strong><select aria-label={tr('Evidence field')} value={field} onChange={e=>setField(e.target.value)}>{['text','owner','due','condition','value','kind'].map(f=><option key={f} value={f}>{tr(f)}</option>)}</select></div>{sources.length?sources.map(source=><div key={source.id}><blockquote>{source.quote}</blockquote><button className="textbutton" onClick={()=>openSource(source)}>{tr('Open in transcript')} <ChevronRight size={14}/></button></div>):<p className="caption">{tr('No source supplied for this field. Keep unsupported values unresolved.')}</p>}</section>
    {!!context.length&&<details className="conversation-context"><summary>{tr('Conversation context')}</summary><p className="caption">{tr('Surrounding turns show what led to this item and what followed. Later proposals do not automatically change an earlier decision.')}</p>{context.map(s=><button className={selected.evidence.some(e=>e.segment_id===s.id)?'context-anchor':''} key={s.id} onClick={()=>openSource({id:s.id,field:'text',quote:s.text,segment_id:s.id,revision:s.revision})}><small>{s.speaker||tr('Unknown speaker')} · {timeLabel(s.start/16000)}</small><span>{s.text}</span></button>)}</details>}
    <details className="action-evolution"><summary>{tr('How this item evolved')}</summary>{items.filter(i=>i.body.subject===selected.body.subject).slice(-12).map(i=><p key={i.id}><strong>{tr(i.body.kind)}</strong> · {i.body.text} <small>({tr(i.review.replaceAll('_',' '))})</small></p>)}</details>
    {!readOnly&&<div className="action-review-buttons"><button disabled={disabled||!canAccept||selected.review==='accepted'} onClick={()=>void decide('accepted')}><Check size={17}/>{tr('Accept & next')}</button><button className="secondary" disabled={disabled||selected.review==='excluded'} onClick={()=>void decide('excluded')}>{tr('Exclude & next')}</button></div>}
    {!readOnly&&<div className="action-edit">{edit(selected,id=>{setSelection(id);setFilter('all');setSearch('');})}</div>}
    <details className="action-history"><summary>{tr('Revision history')}</summary>{history(selected.id)}</details>
   </article>}
  </div>}
 </section>;
}
