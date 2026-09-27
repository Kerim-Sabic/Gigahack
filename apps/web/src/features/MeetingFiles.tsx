import {useState} from 'react';
import {FolderOpen,Copy,RefreshCw} from 'lucide-react';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {api} from '../api';
import {tr} from '../translations';

type Folder={folder:string|null;state:string;error:string|null;updated:number|null};
export function MeetingFiles({meetingId,readOnly}:{meetingId:string;readOnly:boolean}){
 const cache=useQueryClient(),[busy,setBusy]=useState(false),[error,setError]=useState(''),[copied,setCopied]=useState(false);
 const query=useQuery({queryKey:['meeting-files',meetingId],queryFn:()=>api<Folder>(`/meetings/${meetingId}/files`),refetchInterval:3000});
 async function save(){setBusy(true);setError('');try{await api(`/meetings/${meetingId}/files`,'POST');await cache.invalidateQueries({queryKey:['meeting-files',meetingId]});}catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}}
 return <section className="meeting-files"><div><FolderOpen size={20}/><strong>{tr('Meeting folder')}</strong></div><p className="caption">{tr('Keep a local copy of the audio and current transcript. A format template is included until text is available.')}</p>{query.data?.folder&&<><p className="caption">{tr('Local folder copies remain if you delete the meeting in the app.')}</p><code>{query.data.folder}</code><p className="caption" role="status">{tr(query.data.state==='ready'?'Folder saved. Changes sync automatically while the app is running.':query.data.state==='error'?'Could not update the folder. Check free space and folder permissions, then retry.':'Preparing your meeting folder…')}</p></>}{!readOnly&&<button className="secondary" disabled={busy||query.isPending||query.data?.state==='pending'} onClick={()=>void save()}><RefreshCw size={15}/>{tr(query.data?.folder?'Update folder':'Save meeting folder')}</button>}{query.data?.folder&&<button className="textbutton" onClick={async()=>{try{await navigator.clipboard.writeText(query.data!.folder!);setCopied(true);}catch{setError(tr('Select and copy the folder path above.'));}}}><Copy size={15}/>{tr(copied?'Path copied':'Copy folder path')}</button>}{(error||query.isError)&&<p role="alert" className="error">{error||String(query.error)}</p>}</section>;
}
