import { tr } from '../translations';
import { useEffect, useRef, useState } from 'react';
import { api } from '../api';
import type { Labels } from '../i18n';
import { CaptureQueue } from './captureQueue';
type Capture={ctx:AudioContext;stream:MediaStream;node:AudioWorkletNode;id:string;queue:CaptureQueue;gaps:unknown[];pausedAt?:number;flushed?:()=>void};
export function Recorder({meeting,t,done}:{meeting:string;t:Labels;done:()=>void}){
 const [state,setState]=useState<'idle'|'recording'|'paused'|'saving'|'error'>('idle');
 const [saved,setSaved]=useState(0),[level,setLevel]=useState(0),[error,setError]=useState('');
 const control=useRef<Capture|undefined>(undefined);
 useEffect(()=>{const warn=(e:BeforeUnloadEvent)=>{if(control.current){e.preventDefault();e.returnValue='Unacknowledged audio may be lost';}};window.addEventListener('beforeunload',warn);return()=>{window.removeEventListener('beforeunload',warn);control.current?.stream.getTracks().forEach(t=>t.stop());void control.current?.ctx.close();};},[]);
 function failure(e:Error){setError(e.message);setState('error');control.current?.node.port.postMessage('pause');}
 async function start(){
  let stream:MediaStream|undefined,ctx:AudioContext|undefined;
  try{
   setError('');stream=await navigator.mediaDevices.getUserMedia({audio:true});ctx=new AudioContext();await ctx.audioWorklet.addModule('/pcm-worklet.js');
   const r=await api<{id:string}>(`/meetings/${meeting}/recordings`,'POST',{sample_rate:ctx.sampleRate});const node=new AudioWorkletNode(ctx,'pcm-capture');
   const queue=new CaptureQueue(ctx.sampleRate,(seq,pcm)=>api(`/recordings/${r.id}/chunks/${seq}`,'PUT',pcm),ack=>setSaved(ack.acknowledged_samples/ack.sample_rate),failure);
   const c:Capture={ctx,stream,node,id:r.id,queue,gaps:[]};control.current=c;
   node.port.onmessage=e=>{if(e.data instanceof ArrayBuffer){try{queue.enqueue(e.data);}catch(error){failure(error as Error);stream?.getTracks().forEach(track=>track.stop());}}else if(e.data.kind==='flushed'){c.flushed?.();}else if(e.data.kind==='level'){setLevel(e.data.value);}};
   stream.getTracks().forEach(track=>track.onended=()=>failure(new Error('Microphone disconnected. Saved audio is retained.')));
   ctx.createMediaStreamSource(stream).connect(node);const mute=ctx.createGain();mute.gain.value=0;node.connect(mute).connect(ctx.destination);setState('recording');
  }catch(e){stream?.getTracks().forEach(t=>t.stop());void ctx?.close();failure(e as Error);}
 }
 async function stop(){const c=control.current;if(!c)return;setState('saving');try{
  await new Promise<void>((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('Microphone flush timed out.')),5000);c.flushed=()=>{clearTimeout(timer);resolve();};c.node.port.postMessage('stop');});
  c.stream.getTracks().forEach(track=>{track.onended=null;track.stop();});await c.queue.finish();if(!c.queue.nextSequence)throw new Error('No audio was recorded.');
  await api(`/recordings/${c.id}/finish`,'POST',{count:c.queue.nextSequence,gaps:c.gaps});await c.ctx.close();control.current=undefined;setState('idle');setLevel(0);done();
 }catch(e){failure(e as Error);}}
 function pause(){const c=control.current;if(!c)return;if(state==='paused'){c.gaps.push({after_sequence:c.queue.nextSequence-1,wall_duration_ms:Date.now()-(c.pausedAt||Date.now())});c.node.port.postMessage('resume');setState('recording');}else{c.pausedAt=Date.now();c.node.port.postMessage('pause');setState('paused');}}
 return <section className="capture"><div><strong>{t.saved}: {saved.toFixed(1)} s</strong><p>{tr("Confirmed local storage")}</p>{state!=='idle'&&<><meter min={0} max={1} value={level} aria-label="Microphone level"/><span className="caption">{level>.95?'Clipping':level<.01?'Silence':'Microphone active'}</span></>}</div>
 {state==='idle'?<button className="secondary" onClick={start}>{t.record}</button>:<><span role="status">{state}</span><button className="secondary" onClick={pause} disabled={state==='saving'||state==='error'}>{state==='paused'?t.resume:t.pause}</button><button onClick={stop} disabled={state==='saving'}>{t.stop}</button><button className="secondary" onClick={()=>{const c=control.current;c?.gaps.push({bookmark_after_sequence:c.queue.nextSequence-1,acknowledged_seconds:saved});}}>{tr("Bookmark")}</button></>}
 {error&&<div role="alert" className="error">{error}{control.current&&<button className="secondary" onClick={async()=>{try{await control.current?.queue.retry();setError('');setState('paused');}catch(e){failure(e as Error);}}}>{tr("Retry unsaved chunks")}</button>}</div>}</section>;
}
