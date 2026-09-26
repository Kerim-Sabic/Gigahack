import {useCallback,useEffect,useRef,useState} from 'react';
import {Pause,Play,Volume2,VolumeX} from 'lucide-react';
import type {Meeting} from '../api';
import {tr} from '../translations';
import {activeSegment,audioWindow,speakerIndex,speakerPalette,timeLabel,type SpeechSegment} from './transcriptModel';

export function useMeetingAudio(assets:Meeting['assets']){
 const audio=useRef<HTMLAudioElement>(null),windowRef=useRef({asset:'',start:0,end:0}),pending=useRef({time:0,play:false}),generation=useRef(0);
 const [assetId,setAssetId]=useState(''),[current,setCurrent]=useState(0),[playing,setPlaying]=useState(false),[loaded,setLoaded]=useState(false),[error,setError]=useState(''),[muted,setMuted]=useState(false);
 const asset=assets?.find(a=>a.id===assetId)||assets?.[0],duration=asset?asset.samples/asset.sample_rate:0;
 const seek=useCallback((seconds:number,shouldPlay=false,id?:string)=>{
  const target=assets?.find(a=>a.id===(id||asset?.id));const element=audio.current;if(!target||!element)return;
  const total=target.samples/target.sample_rate,position=audioWindow(seconds,total),cached=windowRef.current;
  setError('');setAssetId(target.id);setCurrent(position.target);
  if(cached.asset===target.id&&position.target>=cached.start&&position.target<cached.end&&element.readyState>=1){element.currentTime=position.target-cached.start;if(shouldPlay)void element.play().catch(()=>setError(tr('Audio playback failed. Try again.')));return;}
  const request=++generation.current;
  pending.current={time:position.target-position.start,play:shouldPlay};windowRef.current={asset:target.id,start:position.start,end:position.end};
  element.pause();setLoaded(false);
  element.onloadedmetadata=()=>{if(request!==generation.current)return;element.currentTime=pending.current.time;setLoaded(true);if(pending.current.play)void element.play().catch(()=>setError(tr('Audio playback failed. Try again.')));};
  element.src=`/api/v1/assets/${target.id}/clip?start=${Math.round(position.start*16000)}&end=${Math.round(position.end*16000)}`;element.load();
 },[assets,asset?.id]);
 const toggle=()=>{const element=audio.current;if(!element||!asset)return;if(!element.paused){element.pause();pending.current.play=false;}else seek(current>=duration-.01?0:current,true);};
 useEffect(()=>{let frame=0,last=0;const tick=(now:number)=>{if(now-last>80&&audio.current&&!audio.current.paused){setCurrent(windowRef.current.start+audio.current.currentTime);last=now;}frame=requestAnimationFrame(tick);};if(playing)frame=requestAnimationFrame(tick);return()=>cancelAnimationFrame(frame);},[playing]);
 const onEnded=()=>{if(windowRef.current.end<duration)seek(windowRef.current.end,true);else{setCurrent(duration);setPlaying(false);}};
 const element=<audio ref={audio} preload="none" hidden muted={muted} onPlay={()=>setPlaying(true)} onPause={()=>setPlaying(false)} onTimeUpdate={()=>{if(audio.current?.readyState)setCurrent(windowRef.current.start+audio.current.currentTime);}} onEnded={onEnded} onError={()=>{setError(tr('Audio playback failed. Try again.'));setPlaying(false);}}/>;
 return {element,asset,duration,current,playing,loaded,error,muted,toggle,seek,setMuted};
}
type AudioState=ReturnType<typeof useMeetingAudio>;
export function MeetingAudio({state,segments}:{state:AudioState;segments:SpeechSegment[]}){
 const canvas=useRef<HTMLCanvasElement>(null),surface=useRef<HTMLDivElement>(null),[mini,setMini]=useState(false),[hover,setHover]=useState<number|null>(null);
 useEffect(()=>{const element=surface.current;if(!element)return;const observer=new IntersectionObserver(([entry])=>setMini(!entry.isIntersecting),{threshold:0});observer.observe(element);return()=>observer.disconnect();},[]);
 useEffect(()=>{const element=canvas.current;if(!element)return;
  const draw=()=>{const width=element.clientWidth,height=42,scale=window.devicePixelRatio||1;element.width=width*scale;element.height=height*scale;const ctx=element.getContext('2d');if(!ctx)return;ctx.scale(scale,scale);ctx.clearRect(0,0,width,height);
   if(!state.duration)return;
   for(const segment of segments){const x=segment.start/16000/state.duration*width,end=segment.end/16000/state.duration*width;ctx.fillStyle=speakerPalette[speakerIndex(segment.speaker)];for(let pos=x;pos<Math.max(x+2,end);pos+=5)ctx.fillRect(pos,9,Math.min(2.5,Math.max(2,end-pos)),24);}
  };const observer=new ResizeObserver(draw);observer.observe(element);draw();return()=>observer.disconnect();
 },[segments,state.duration]);
 const range=(compact=false)=><input className={compact?'mini-seek':'activity-seek'} type="range" aria-label={tr('Seek recording')} aria-valuetext={`${timeLabel(state.current)} / ${timeLabel(state.duration)}`} min={0} max={state.duration||1} step={.1} value={Math.min(state.current,state.duration)} disabled={!state.duration} onChange={e=>state.seek(Number(e.target.value),state.playing)}/>;
 const playButton=<button className="audio-play" aria-label={tr(state.playing?'Pause recording':'Play recording')} disabled={!state.asset} onClick={state.toggle}>{state.playing?<Pause size={25} fill="currentColor" strokeWidth={1}/>:<Play size={25} fill="currentColor" strokeWidth={1}/>}</button>;
 return <>{state.element}<div className="audio-experience" ref={surface}>{playButton}<div className="audio-track"><div className="activity-line" onPointerMove={e=>{const box=e.currentTarget.getBoundingClientRect();setHover(Math.max(0,Math.min(1,(e.clientX-box.left)/box.width))*state.duration);}} onPointerLeave={()=>setHover(null)} title={hover===null?tr('Speaker activity'):timeLabel(hover)}><canvas ref={canvas} aria-hidden="true"/><div className="audio-playhead" style={{left:`${state.duration?state.current/state.duration*100:0}%`,background:speakerPalette[speakerIndex(activeSegment(segments,state.current)?.speaker||null)]}} aria-hidden="true"/>{range()}</div><div className="audio-times"><span>{timeLabel(state.current)}</span><span>{timeLabel(state.duration)}</span></div></div></div>{state.error&&<p className="error" role="alert">{state.error}</p>}
 {mini&&state.loaded&&<div className="mini-player">{playButton}<span>{timeLabel(state.current)}</span>{range(true)}<span>{timeLabel(state.duration)}</span><button className="icon-button" aria-label={tr(state.muted?'Unmute':'Mute')} onClick={()=>state.setMuted(!state.muted)}>{state.muted?<VolumeX size={18}/>:<Volume2 size={18}/>}</button></div>}</>;
}
