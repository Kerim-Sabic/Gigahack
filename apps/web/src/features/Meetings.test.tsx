// @vitest-environment jsdom
import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Meetings } from './Meetings';
import { strings } from '../i18n';

afterEach(()=>{cleanup();vi.unstubAllGlobals();});
describe('meeting form',()=>{
 it('shows a server failure and never navigates on unsuccessful creation',async()=>{
  const open=vi.fn();
  vi.stubGlobal('fetch',vi.fn(async(_url:string,options?:RequestInit)=>({ok:options?.method!=='POST',json:async()=>options?.method==='POST'?{code:'revision_conflict'}:[]})));
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><Meetings canCreate={true} t={strings.en} open={open}/></QueryClientProvider>);
  await screen.findByText('Your next meeting starts here.');
  fireEvent.click(screen.getByRole('button',{name:'＋ New meeting'}));
  fireEvent.change(screen.getByLabelText('Meeting title'),{target:{value:'Synthetic'}});
  fireEvent.submit(screen.getByRole('button',{name:'Create meeting'}).closest('form')!);
  await waitFor(()=>expect(screen.getByRole('alert').textContent).toContain('This record changed.'));
  expect(open).not.toHaveBeenCalled();
 });
 it('does not offer creation to a viewer',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>[]})));
  render(<QueryClientProvider client={new QueryClient()}><Meetings canCreate={false} t={strings.en} open={vi.fn()}/></QueryClientProvider>);
  await screen.findByText('No meetings have been shared with you yet.');
  expect(screen.queryByRole('button',{name:/New meeting/})).toBeNull();
 });
 it('keeps localization keys synchronized',()=>{
  expect(Object.keys(strings.ro)).toEqual(Object.keys(strings.en));
  expect(Object.keys(strings.ru)).toEqual(Object.keys(strings.en));
 });
});
