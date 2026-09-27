// @vitest-environment jsdom
import React from 'react';
import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {AudioIntake} from './AudioIntake';
import {ExtractActions} from './ExtractActions';
import {api,uploadAudio,type Meeting} from '../api';
vi.mock('../api',()=>({api:vi.fn(),uploadAudio:vi.fn()}));
afterEach(()=>{cleanup();vi.clearAllMocks();});
const meeting={id:'meeting',assets:[]} as unknown as Meeting;
it('validates audio selection and saves explicitly without starting transcription',async()=>{
 const saved=vi.fn(async()=>{}),transcribe=vi.fn();
 vi.mocked(uploadAudio).mockResolvedValue();
 render(<AudioIntake meeting={meeting} disabled={false} saved={saved} transcribe={transcribe}/>);
 const input=screen.getByLabelText('Choose audio file');
 fireEvent.change(input,{target:{files:[new File(['bad'],'notes.txt')]}});
 expect(screen.getByRole('alert').textContent).toContain('Choose a WAV');
 fireEvent.change(input,{target:{files:[new File(['audio'],'meeting.M4A')]}});
 expect(uploadAudio).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Upload recording'}));
 await waitFor(()=>expect(saved).toHaveBeenCalledOnce());
 expect(uploadAudio).toHaveBeenCalledWith('meeting',expect.objectContaining({name:'meeting.M4A'}),expect.any(Function));
 expect(transcribe).not.toHaveBeenCalled();
});
it('shows upload errors and retains the selected recording for retry',async()=>{
 vi.mocked(uploadAudio).mockRejectedValue(new Error('Storage full'));
 render(<AudioIntake meeting={meeting} disabled={false} saved={vi.fn()} transcribe={vi.fn()}/>);
 fireEvent.change(screen.getByLabelText('Choose audio file'),{target:{files:[new File(['audio'],'meeting.wav')]}});
 fireEvent.click(screen.getByRole('button',{name:'Upload recording'}));
 await waitFor(()=>expect(screen.getByRole('alert').textContent).toBe('Storage full'));
 expect(screen.getByText('meeting.wav')).toBeTruthy();
});
it('extracts only the selected saved transcript without enabling speech stages',async()=>{
 vi.mocked(api).mockResolvedValue({id:'job',state:'queued'});
 const result=vi.fn();
 const props={meetingId:'meeting',assetId:'asset',device:'cuda',disabled:false,hasTranscript:true,onResult:result,act:async(fn:()=>Promise<unknown>)=>{await fn();}};
 const view=render(<ExtractActions {...props} jobs={[]}/>);
 fireEvent.click(screen.getByRole('button',{name:'Extract actions with AI'}));
 await waitFor(()=>expect(result).toHaveBeenCalledOnce());
 expect(api).toHaveBeenCalledExactlyOnceWith('/meetings/meeting/jobs','POST',{asset_id:'asset',device:'cuda',transcript_only:true});
 view.rerender(<ExtractActions {...props} jobs={[{id:'job',state:'complete'}] as Meeting['jobs']}/>);
 expect(screen.getByRole('status').textContent).toBe('Analysis saved. Ready for review.');
});
it('prevents extraction without text and while processing is busy',()=>{
 const props={meetingId:'meeting',assetId:'asset',device:'cuda',onResult:vi.fn(),act:vi.fn(),jobs:[]};
 const view=render(<ExtractActions {...props} disabled={false} hasTranscript={false}/>);
 expect((screen.getByRole('button') as HTMLButtonElement).disabled).toBe(true);
 view.rerender(<ExtractActions {...props} disabled={true} hasTranscript={true}/>);
 expect((screen.getByRole('button') as HTMLButtonElement).disabled).toBe(true);
 expect(api).not.toHaveBeenCalled();
});
it('retries an existing cancelled text analysis instead of creating duplicate work',async()=>{
 vi.mocked(api).mockResolvedValueOnce({id:'cancelled-job',state:'cancelled'}).mockResolvedValueOnce({ok:true});
 render(<ExtractActions meetingId="meeting" assetId="asset" device="cpu" jobs={[]} disabled={false} hasTranscript onResult={vi.fn()} act={async fn=>{await fn();}}/>);
 fireEvent.click(screen.getByRole('button',{name:'Extract actions with AI'}));
 await waitFor(()=>expect(api).toHaveBeenLastCalledWith('/jobs/cancelled-job/retry','POST'));
});
