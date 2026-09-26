export type SpeechSegment = {id:string;asset_id:string;start:number;end:number;text:string;speaker:string|null;revision:number;raw:string;alternatives:string;words?:string};
export const speakerPalette = ['#80618F','#526F89','#5C796D','#A15C73','#8C7149','#6A6B9A'];
// One accessible, muted identity color across name, dot, key and recording timeline.
export const speakerInk = speakerPalette;
export function speakerIndex(name:string|null){
 if(!name)return 5;
 const number=name.match(/(?:speaker[ _-]*)(\d+)$/i);
 if(number)return Math.max(0,Number(number[1])-(name.includes('_')?0:1))%speakerPalette.length;
 let hash=0;for(const character of name)hash=(hash*31+character.charCodeAt(0))>>>0;
 return hash%speakerPalette.length;
}
export function timeLabel(seconds:number){
 const value=Math.max(0,Math.floor(Number.isFinite(seconds)?seconds:0)),h=Math.floor(value/3600),m=Math.floor(value%3600/60),s=String(value%60).padStart(2,'0');
 return h?`${h}:${String(m).padStart(2,'0')}:${s}`:`${m}:${s}`;
}
export function audioWindow(seconds:number,total:number){
 const target=Math.max(0,Math.min(seconds,Math.max(0,total-.001))),start=Math.floor(target/600)*600;
 return {target,start,end:Math.min(total,start+600)};
}
export function activeSegment(segments:SpeechSegment[],seconds:number){
 const sample=seconds*16000;
 // Segment list is time ordered. Binary search avoids rescanning a long meeting on every tick.
 let left=0,right=segments.length;
 while(left<right){const middle=(left+right)>>>1;if(segments[middle].start<=sample)left=middle+1;else right=middle;}
 for(let i=left-1;i>=0;i--)if(segments[i].end>sample)return segments[i];
 return undefined;
}
