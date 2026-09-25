// @vitest-environment jsdom
import React from 'react';
import { afterEach, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { JobProgress } from './JobProgress';
import type { components } from '../generated/api';
type Job = components['schemas']['JobView'];
afterEach(cleanup);
it('does not show a failed job as waiting or progressing',()=>{
 render(<JobProgress job={{state:'failed',progress:null} as Job}/>);
 expect(screen.queryByRole('progressbar')).toBeNull();
 expect(screen.getByText(/Processing stopped/)).toBeTruthy();
});
it('does not claim completion from 100 percent stage progress',()=>{
 render(<JobProgress job={{state:'running',progress:{stage:'whisper',phase:'transcribing',completed:10,total:10,unit:'seconds',elapsed_seconds:3,eta_seconds:0,eta_scope:'current_phase',updated_at:Date.now()/1000}} as Job}/>);
 expect(screen.queryByText('Analysis saved. Ready for review.')).toBeNull();
 expect(screen.getByText(/Later steps and human review are not included/)).toBeTruthy();
});
