// @vitest-environment jsdom
import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Templates } from './Templates';

const template={classification:'Administrative',version:0,titles:{en:'Original',ro:'',ru:''},introduction:'',recipient_group_id:null};
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it('keeps failed edits and refuses to silently adopt a concurrent template version',async()=>{
  vi.stubGlobal('fetch',vi.fn(async(url:string,options?:RequestInit)=>({ok:options?.method!=='PUT',json:async()=>options?.method==='PUT'?{code:'revision_conflict'}:url.endsWith('/settings/templates')?[template]:[]})));
  const cache=new QueryClient({defaultOptions:{queries:{retry:false}}});
  render(<QueryClientProvider client={cache}><Templates role="admin"/></QueryClientProvider>);
  const title=await screen.findByLabelText('English document heading') as HTMLInputElement;
  fireEvent.change(title,{target:{value:'Unsaved custom title'}});
  fireEvent.submit(screen.getByRole('button',{name:'Save template'}).closest('form')!);
  await waitFor(()=>expect(screen.getByRole('alert').textContent).toContain('This record changed.'));
  expect(title.value).toBe('Unsaved custom title');
  expect(screen.queryByText('Saved on this computer.')).toBeNull();
  act(()=>cache.setQueryData(['templates'],[{...template,version:2,titles:{...template.titles,en:'Concurrent title'}}]));
  expect(title.value).toBe('Unsaved custom title');
  fireEvent.click(await screen.findByRole('button',{name:'Replace my edits with saved template'}));
  expect(title.value).toBe('Concurrent title');
});
it('shows templates without edit controls to a secretary',async()=>{
  vi.stubGlobal('fetch',vi.fn(async(url:string)=>({ok:true,json:async()=>url.endsWith('/settings/templates')?[template]:[]})));
  render(<QueryClientProvider client={new QueryClient()}><Templates role="secretary"/></QueryClientProvider>);
  const title=await screen.findByLabelText('English document heading') as HTMLInputElement;
  expect(title.readOnly).toBe(true);
  expect(screen.queryByRole('button',{name:'Save template'})).toBeNull();
});
