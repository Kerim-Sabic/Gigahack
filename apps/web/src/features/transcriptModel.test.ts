import {expect,it} from 'vitest';
import {activeSegment,audioWindow,speakerIndex,timeLabel,type SpeechSegment} from './transcriptModel';
it('seeks across ten-minute windows without losing the recording offset',()=>{
 expect(audioWindow(650,702.549)).toEqual({target:650,start:600,end:702.549});
 expect(audioWindow(600,7200)).toEqual({target:600,start:600,end:1200});
 expect(audioWindow(-1,702).target).toBe(0);
 expect(audioWindow(900,702).target).toBeLessThan(702);
 expect(timeLabel(702.549)).toBe('11:42');expect(timeLabel(7201)).toBe('2:00:01');
});
it('speaker color assignment does not depend on search or pagination',()=>{
 expect(speakerIndex('Speaker 1')).toBe(0);expect(speakerIndex('Speaker 2')).toBe(1);
 expect(speakerIndex('SPEAKER_00')).toBe(0);expect(speakerIndex('SPEAKER_01')).toBe(1);
 expect(speakerIndex('Андрей')).toBe(speakerIndex('Андрей'));
});
it('finds active short, overlapping and late segments while keeping silence unselected',()=>{
 const segments=[{id:'a',start:0,end:32000},{id:'b',start:32000,end:48000},{id:'c',start:32000,end:64000},{id:'d',start:9600000,end:9616000}] as SpeechSegment[];
 expect(activeSegment(segments,0)?.id).toBe('a');expect(activeSegment(segments,2)?.id).toBe('c');
 expect(activeSegment(segments,5)).toBeUndefined();expect(activeSegment(segments,600.5)?.id).toBe('d');
});
