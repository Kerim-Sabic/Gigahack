// @vitest-environment jsdom
import React from 'react';
import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {MeetingSummary} from './MeetingSummary';
import {api} from '../api';
vi.mock('../api',()=>({api:vi.fn()}));
afterEach(()=>{cleanup();vi.clearAllMocks();});
const props={meetingId:'m',revision:3,device:'cuda',disabled:false,readOnly:false,act:async(fn:()=>Promise<unknown>)=>{await fn();},showSource:vi.fn()};
function mount(overrides={}){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MeetingSummary {...props} {...overrides}/></QueryClientProvider>);}
it('generates from the meeting transcript and provides source navigation',async()=>{
 vi.mocked(api).mockResolvedValue({has_transcript:true,job:null,summary:{stale:false,body:{points:[{text:'The date is unresolved.',source_ids:['s']}]}}});
 mount();
 await screen.findByText('The date is unresolved.');
 fireEvent.click(screen.getByRole('button',{name:'Source 1'}));
 expect(props.showSource).toHaveBeenCalledWith('s');
 fireEvent.click(screen.getByRole('button',{name:'Regenerate summary'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('/meetings/m/summary','POST',{revision:3,device:'cuda'}));
});
it('shows stale drafts and hides generation from viewers',async()=>{
 vi.mocked(api).mockResolvedValue({has_transcript:true,job:null,summary:{stale:true,body:{points:[{text:'Old draft',source_ids:['s']}]}}});
 mount({readOnly:true});
 await screen.findByText('The transcript or meeting details changed. Regenerate the summary before creating minutes.');
 expect(screen.queryByRole('button',{name:'Regenerate summary'})).toBeNull();
});
it('prevents generation without transcript',async()=>{
 vi.mocked(api).mockResolvedValue({has_transcript:false,job:null,summary:null});
 mount();
 await screen.findByText('Add a transcript to generate a meeting summary.');
 expect((screen.getByRole('button',{name:'Generate summary'}) as HTMLButtonElement).disabled).toBe(true);
});
