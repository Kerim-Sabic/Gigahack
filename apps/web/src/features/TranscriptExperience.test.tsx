// @vitest-environment jsdom
import React from 'react';
import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {TranscriptExperience} from './TranscriptExperience';
import type {SpeechSegment} from './transcriptModel';
afterEach(cleanup);
const source={id:'s',asset_id:'a',start:32000,end:48000,text:'Așa. Да. Ștefan.',speaker:'Speaker 2',revision:1,raw:'{}',alternatives:'[]'};
function view(rows:SpeechSegment[],save=vi.fn().mockResolvedValue(undefined),readOnly=false){
 const seek=vi.fn();render(<QueryClientProvider client={new QueryClient()}><TranscriptExperience segments={rows} readOnly={readOnly} seek={seek} save={save} busy={false}/></QueryClientProvider>);return {seek,save};
}
it('keeps a long transcript DOM bounded and searches Cyrillic beyond the first page',()=>{
 const rows=Array.from({length:2001},(_,i)=>({...source,id:String(i),text:i===2000?'Аха. Окей.':'S-a pornit parcă.'}));
 view(rows);expect(document.querySelectorAll('.utterance')).toHaveLength(80);
 fireEvent.change(screen.getByRole('textbox',{name:'Search transcript'}),{target:{value:'окей'}});
 expect(document.querySelectorAll('.utterance')).toHaveLength(1);expect(document.querySelector('mark')?.textContent).toBe('Окей');
});
it('supports timestamp seek, cancellation and keyboard save without changing source until saved',async()=>{
 const {seek,save}=view([source]);fireEvent.click(screen.getByRole('button',{name:'Play from 0:02'}));expect(seek).toHaveBeenCalledWith(source);
 fireEvent.click(screen.getByRole('button',{name:'Edit transcript'}));
 fireEvent.change(screen.getByRole('textbox',{name:'Transcript text'}),{target:{value:'Changed'}});
 fireEvent.keyDown(screen.getByRole('textbox',{name:'Transcript text'}),{key:'Escape'});expect(save).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Edit transcript'}));expect((screen.getByRole('textbox',{name:'Transcript text'}) as HTMLTextAreaElement).value).toBe(source.text);
 fireEvent.change(screen.getByRole('combobox',{name:'Speaker'}),{target:{value:'Speaker 3'}});
 fireEvent.keyDown(screen.getByRole('textbox',{name:'Transcript text'}),{key:'Enter',ctrlKey:true});
 await waitFor(()=>expect(save).toHaveBeenCalledWith(source,source.text,'Speaker 3'));
});
it('retains the editor when persistence fails, and hides editing for viewers',async()=>{
 const save=vi.fn().mockRejectedValue(new Error('revision conflict'));view([source],save);
 fireEvent.click(screen.getByRole('button',{name:'Edit transcript'}));fireEvent.click(screen.getByRole('button',{name:'Save'}));
 await screen.findByRole('alert');expect(screen.getByRole('textbox',{name:'Transcript text'})).toBeTruthy();
 cleanup();view([source],vi.fn(),true);expect(screen.queryByRole('button',{name:'Edit transcript'})).toBeNull();
});
