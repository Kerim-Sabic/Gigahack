// @vitest-environment jsdom
import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AudioChecks } from './AudioChecks';
import { api } from '../api';
vi.mock('../api',()=>({api:vi.fn()}));
afterEach(()=>{cleanup();vi.clearAllMocks();});
it('plays the original asset interval and pages through review observations',async()=>{
 vi.mocked(api).mockImplementation(async(path)=>({asset_id:'source-audio',total:21,items:[{kind:'speech_without_transcript',start:path.includes('offset=20')?32000:16000,end:48000,hypotheses:[{text:'Обсудим cererea.',attempt:'short_retry',source_start:0,source_end:64000}]}]}));
 const play=vi.fn();
 render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><AudioChecks jobId="job" running={false} play={play}/></QueryClientProvider>);
 fireEvent.click(await screen.findByRole('button',{name:/Play passage 1.0/}));
 expect(play).toHaveBeenCalledWith(expect.objectContaining({asset_id:'source-audio',start:16000,end:48000}));
 expect(screen.getByText(/These automated flags may be wrong/)).toBeTruthy();
 expect(screen.getByText('Обсудим cererea.')).toBeTruthy();
 expect(screen.getByText(/It has not been added to the transcript/)).toBeTruthy();
 fireEvent.click(screen.getByText('Recovery hypothesis · shorter retry'));
 fireEvent.click(screen.getByRole('button',{name:/Play recovery context/}));
 expect(play).toHaveBeenLastCalledWith({asset_id:'source-audio',start:0,end:64000});
 fireEvent.click(screen.getByRole('button',{name:'Next'}));
 expect(await screen.findByRole('button',{name:/Play passage 2.0/})).toBeTruthy();
});
