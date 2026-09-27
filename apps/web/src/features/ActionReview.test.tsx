// @vitest-environment jsdom
import React from 'react';
import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {ActionReview} from './ActionReview';
afterEach(cleanup);
const items=['Send report','Check schedule'].map((text,i)=>({id:String(i),review:'pending',body:{subject:String(i),text,category:'action',kind:'confirm',owner:'Maria',due:'2026-10-16',uncertainties:[]},evidence:[]}));
const props={items,segments:[],disabled:false,canAccept:true,readOnly:false,review:vi.fn(async()=>true),openSource:vi.fn(),edit:()=>null,history:()=>null};
it('advances only after a successful review and preserves selection on failed save',async()=>{
 const review=vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
 render(<ActionReview {...props} review={review}/>);
 fireEvent.click(screen.getByRole('button',{name:'Accept & next'}));
 await waitFor(()=>expect(review).toHaveBeenCalledTimes(1));
 expect(screen.getByRole('heading',{level:3}).textContent).toBe('Send report');
 fireEvent.click(screen.getByRole('button',{name:'Accept & next'}));
 await waitFor(()=>expect(screen.getByRole('heading',{level:3}).textContent).toBe('Check schedule'));
});
it('searches owners and separates reviewed items without accepting proposals automatically',()=>{
 render(<ActionReview {...props} items={[items[0],{...items[1],review:'accepted'}]}/>);
 expect(screen.queryByText('Check schedule')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Reviewed'}));
 expect(screen.getByRole('heading',{level:3}).textContent).toBe('Check schedule');
 fireEvent.change(screen.getByRole('searchbox'),{target:{value:'missing'}});
 expect(screen.getByText('No items in this view')).toBeTruthy();
});
it('does not expose editing or acceptance to a read-only user',()=>{
 const edit=vi.fn(()=>null);
 render(<ActionReview {...props} readOnly edit={edit}/>);
 expect(screen.queryByRole('button',{name:'Accept & next'})).toBeNull();
 expect(edit).not.toHaveBeenCalled();
});
it('keeps a saved correction visible when it moves out of the pending list',()=>{
 const edit:React.ComponentProps<typeof ActionReview>['edit']=(_item,select)=><button onClick={()=>select('corrected')}>Save edit</button>;
 const view=render(<ActionReview {...props} edit={edit}/>);
 fireEvent.click(screen.getByRole('button',{name:'Save edit'}));
 view.rerender(<ActionReview {...props} items={[...items,{...items[0],id:'corrected',review:'accepted',body:{...items[0].body,text:'Corrected action'}}]} edit={edit}/>);
 expect(screen.getByRole('heading',{level:3}).textContent).toBe('Corrected action');
});
