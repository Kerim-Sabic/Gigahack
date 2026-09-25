import {describe,expect,it} from 'vitest';
import {CaptureQueue} from './captureQueue';
describe('durable capture controller',()=>{
 it('retries the same sequence after lost acknowledgement',async()=>{const calls:number[]=[];let failed=false,saved=0;const q=new CaptureQueue(16000,async(sequence,data)=>{calls.push(sequence);if(!failed){failed=true;throw new Error('network lost');}return {acknowledged_samples:data.byteLength/2,sample_rate:16000};},a=>{saved=a.acknowledged_samples;},()=>{});q.enqueue(new ArrayBuffer(64000));await q.finish();expect(calls).toEqual([0,0]);expect(saved).toBe(32000);expect(q.pendingSamples).toBe(0);});
 it('retains failures for explicit retry and bounds memory',async()=>{let online=false;const q=new CaptureQueue(10,async()=>{if(!online)throw new Error('offline');return {acknowledged_samples:20,sample_rate:10};},()=>{},()=>{});q.enqueue(new ArrayBuffer(40));await q.drain();expect(q.error).not.toBeNull();expect(q.pendingSamples).toBe(20);expect(()=>q.enqueue(new ArrayBuffer(1200))).toThrow('60 seconds');online=true;await q.retry();expect(q.pendingSamples).toBe(0);expect(q.nextSequence).toBe(1);});
});
