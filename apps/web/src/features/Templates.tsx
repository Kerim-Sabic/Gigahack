import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import { tr } from '../translations';
import type { components } from '../generated/api';

type Template = components['schemas']['TemplateView'];
type Group = {id:string;name:string;addresses:string[];version:number};

export function Templates({role}:{role:string}) {
  const templates=useQuery({queryKey:['templates'],queryFn:()=>api<Template[]>('/settings/templates')});
  const groups=useQuery({queryKey:['groups'],queryFn:()=>api<Group[]>('/recipient-groups')});
  return <>
    <p className="eyebrow">{tr('DOCUMENT TEMPLATES')}</p><h1>{tr('Templates')}</h1>
    <p>{tr('Meeting classification selects a template. Existing previews keep their saved template and content.')}</p>
    <p className="notice">{tr('A suggested recipient group never authorizes sending. Review the exact addresses before delivery.')}</p>
    {templates.isPending&&<p role="status">{tr('Loading…')}</p>}
    {(templates.isError||groups.isError)&&<p role="alert" className="error">{String(templates.error||groups.error)}</p>}
    {templates.data?.map(template=><TemplateEditor key={template.classification} template={template} groups={groups.data||[]} editable={role==='admin'}/>) }
  </>;
}

function TemplateEditor({template,groups,editable}:{template:Template;groups:Group[];editable:boolean}) {
  const [draft,setDraft]=useState(template),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const cache=useQueryClient();
  async function save(event:React.FormEvent<HTMLFormElement>) {
    event.preventDefault();setBusy(true);setError('');setNotice('');
    try {
      const saved=await api<Template>('/settings/templates/'+encodeURIComponent(draft.classification),'PUT',{
        version:draft.version,titles:draft.titles,introduction:draft.introduction,recipient_group_id:draft.recipient_group_id
      });
      setDraft(saved);cache.setQueryData<Template[]>(['templates'],old=>old?.map(t=>t.classification===saved.classification?saved:t));
      setNotice(tr('Saved on this computer.'));
    } catch (failure) {setError(failure instanceof Error?failure.message:tr('The request failed. Check the form, refresh, and try again.'));}
    finally {setBusy(false);}
  }
  return <section className="card"><h2>{tr(template.classification)} <span className="badge">{tr('Version')} {draft.version}</span></h2>
    <p className="caption">{tr('Required decisions, actions, unresolved matters and amendment history are always included.')}</p>
    {error&&<p role="alert" className="error">{error}</p>}{notice&&<p role="status">{notice}</p>}
    {template.version!==draft.version&&<p className="notice">{tr('A newer template is available. Your edits have been kept.')} <button className="secondary" onClick={()=>{setDraft(template);setError('');}}>{tr('Replace my edits with saved template')}</button></p>}
    <form onSubmit={save}><fieldset disabled={busy} className="mutation-controls">
      {(['en','ro','ru'] as const).map((language,index)=><label key={language}>{tr(['English document heading','Romanian document heading','Russian document heading'][index])}
        <input readOnly={!editable} maxLength={120} value={draft.titles[language]||''} onChange={e=>setDraft({...draft,titles:{...draft.titles,[language]:e.target.value}})} placeholder={tr('Leave blank for the standard heading')}/>
      </label>)}
      <label>{tr('Document introduction')}<textarea readOnly={!editable} maxLength={1000} rows={3} value={draft.introduction||''} onChange={e=>setDraft({...draft,introduction:e.target.value})}/></label>
      <p className="caption">{tr('Plain text only. Enter approved organizational wording; it is not translated automatically.')}</p>
      <label>{tr('Suggested recipient group')}<select aria-label={tr('Suggested recipient group')} disabled={!editable} value={draft.recipient_group_id||''} onChange={e=>setDraft({...draft,recipient_group_id:e.target.value||null})}>
        <option value="">{tr('No suggested group')}</option>{groups.map(group=><option key={group.id} value={group.id}>{group.name}</option>)}
      </select></label>
      {editable?<button disabled={busy}>{tr(busy?'Saving…':'Save template')}</button>:<p>{tr('Admin access required to edit templates.')}</p>}
    </fieldset></form>
  </section>;
}
