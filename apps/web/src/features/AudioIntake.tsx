import {useRef,useState} from 'react';
import {FileAudio,UploadCloud,CheckCircle2} from 'lucide-react';
import {type Meeting,uploadAudio} from '../api';
import {tr} from '../translations';
import {timeLabel} from './transcriptModel';

export function recordingName(asset:NonNullable<Meeting['assets']>[number],index=0){
 try{const meta=JSON.parse(asset.original);if(meta.filename)return String(meta.filename);}catch{/* Older recordings have no filename. */}
 return `${tr('Recording')} ${index+1}`;
}
export function AudioIntake({meeting,disabled,saved,transcribe}:{meeting:Meeting;disabled:boolean;saved:()=>Promise<void>;transcribe:(id:string)=>void}){
 const input=useRef<HTMLInputElement>(null);
 const [file,setFile]=useState<File>(),[progress,setProgress]=useState<number|null>(null),[uploading,setUploading]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[drag,setDrag]=useState(false);
 function choose(files:FileList|null){
  if(disabled||uploading)return;setError('');setNotice('');setFile(undefined);
  if(!files?.length)return;
  if(files.length!==1){setError(tr('Choose one recording at a time.'));return;}
  const next=files[0];
  if(!/\.(wav|mp3|m4a|ogg|flac|webm)$/i.test(next.name)){setError(tr('Choose a WAV, MP3, M4A, OGG, FLAC or WebM audio file.'));return;}
  if(!next.size){setError(tr('This file is empty. Choose another recording.'));return;}
  setFile(next);
 }
 async function upload(){
  if(!file||uploading)return;setUploading(true);setError('');setNotice('');setProgress(0);
  try{await uploadAudio(meeting.id,file,setProgress);setFile(undefined);if(input.current)input.current.value='';setNotice(tr('Audio saved. Choose Transcribe audio when you are ready.'));await saved();}
  catch(e){setError(e instanceof Error?e.message:String(e));}
  finally{setUploading(false);setProgress(null);}
 }
 return <section className="audio-intake" aria-label={tr('Audio recordings')}>
  <div className="intake-heading"><div><h2>{tr('Audio recordings')}</h2><p>{tr('Upload a recording, then transcribe it when you are ready.')}</p></div><FileAudio size={25} aria-hidden="true"/></div>
  <div className={`audio-dropzone ${drag?'dragging':''}`} onDragOver={e=>{e.preventDefault();if(!disabled&&!uploading)setDrag(true);}} onDragLeave={()=>setDrag(false)} onDrop={e=>{e.preventDefault();setDrag(false);choose(e.dataTransfer.files);}}>
   <UploadCloud size={28} aria-hidden="true"/>
   <div><strong>{file?file.name:tr('Drop your audio recording here')}</strong><p>{file?`${(file.size/1024/1024).toFixed(1)} MB`:tr('WAV, MP3, M4A, OGG, FLAC or WebM')}</p></div>
   <input ref={input} hidden aria-hidden="true" tabIndex={-1} className="audio-file-input" type="file" accept=".wav,.mp3,.m4a,.ogg,.flac,.webm" aria-label={tr('Choose audio file')} disabled={disabled||uploading} onChange={e=>choose(e.target.files)}/>
   <button className="secondary" disabled={disabled||uploading} onClick={()=>{if(input.current){input.current.value='';input.current.click();}}}>{tr(file?'Change file':'Choose audio file')}</button>
  </div>
  {file&&<div className="intake-upload"><span className="caption">{tr('Audio stays on this computer. Uploading does not start transcription.')}</span><button disabled={disabled||uploading} onClick={()=>void upload()}>{tr(uploading?'Saving audio…':'Upload recording')}</button></div>}
  {uploading&&<div className="upload-progress" role="status"><progress aria-label={tr('Audio upload progress')} max={100} value={progress===null?undefined:progress}/><p>{progress===null?tr('Checking and preparing audio…'): `${tr('Uploading audio')} ${progress}%`}</p><small>{tr('Keep this page open until the recording is saved.')}</small></div>}
  {error&&<p className="error" role="alert">{error}</p>}{notice&&<p role="status" className="caption"><CheckCircle2 size={15} aria-hidden="true"/> {notice}</p>}
  {!!meeting.assets?.length&&<div className="saved-recordings">{meeting.assets.map((a,i)=><div className="saved-recording" key={a.id}><FileAudio size={21} aria-hidden="true"/><div><strong>{recordingName(a,i)}</strong><small>{timeLabel(a.samples/a.sample_rate)} · {tr('Saved on this computer')}</small></div><button className="secondary" disabled={disabled||uploading} onClick={()=>transcribe(a.id)}>{tr('Transcribe audio')}</button></div>)}</div>}
 </section>;
}
