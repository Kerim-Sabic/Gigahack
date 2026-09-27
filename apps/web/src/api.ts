import { z } from 'zod';
import { errorMessage } from './errors';
import { tr } from './translations';
export let csrf = '';
export const setCsrf = (token: string) => { csrf = token; };
export function uploadAudio(meetingId:string,file:File,progress:(percent:number|null)=>void):Promise<void>{
 return new Promise((resolve,reject)=>{
  const request=new XMLHttpRequest(),form=new FormData();form.append('file',file);
  request.open('POST',`/api/v1/meetings/${meetingId}/uploads`);
  request.setRequestHeader('X-CSRF-Token',csrf);
  request.upload.onprogress=e=>progress(e.lengthComputable?Math.min(99,Math.round(e.loaded/e.total*100)):null);
  request.upload.onload=()=>progress(null);
  request.onerror=()=>reject(new Error(tr('Cannot reach the local service. Check that Secure MOM is running.')));
  request.onload=()=>{if(request.status>=200&&request.status<300){resolve();return;}let code='validation_failed';try{code=JSON.parse(request.responseText).code||code;}catch{/* Non-JSON gateway failures. */}reject(new Error(errorMessage(code)));};
  request.send(form);
 });
}
export async function api<T = any>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const raw = body instanceof FormData || body instanceof ArrayBuffer;
  const r = await fetch('/api/v1' + path, {method, headers: {...(raw ? {} : {'Content-Type': 'application/json'}), 'X-CSRF-Token': csrf}, body: body === undefined ? undefined : raw ? body as BodyInit : JSON.stringify(body)}).catch(() => {throw new Error(tr('Cannot reach the local service. Check that Secure MOM is running.'));});
  const json = await r.json();
  if (!r.ok) throw new Error(errorMessage(z.object({code: z.string().optional(), detail: z.unknown().optional()}).parse(json).code || 'validation_failed'));
  return json;
}
import type { components } from './generated/api';
export type Meeting = components['schemas']['MeetingView'] & Partial<Pick<components['schemas']['MeetingDetail'], 'assets'|'jobs'|'participants'|'recordings'|'transcript_pending_assets'>>;
