class CaptureProcessor extends AudioWorkletProcessor {
 constructor(){super();this.parts=[];this.length=0;this.levelSamples=0;this.energy=0;this.paused=false;this.port.onmessage=e=>{if(e.data==='stop'){this.paused=true;this.flush();this.port.postMessage({kind:'flushed'});}else if(e.data==='pause'){this.paused=true;this.flush();}else if(e.data==='flush'){this.flush();}else this.paused=false;};}
 flush(){if(!this.length)return;const pcm=new Int16Array(this.length);let offset=0;for(const part of this.parts){for(let i=0;i<part.length;i++)pcm[offset++]=Math.max(-1,Math.min(1,part[i]))*32767;}this.port.postMessage(pcm.buffer,[pcm.buffer]);this.parts=[];this.length=0;}
 process(inputs){const audio=inputs[0]?.[0];if(audio&&!this.paused){this.parts.push(audio.slice());this.length+=audio.length;for(const sample of audio)this.energy+=sample*sample;this.levelSamples+=audio.length;if(this.levelSamples>=sampleRate/4){this.port.postMessage({kind:'level',value:Math.sqrt(this.energy/this.levelSamples)});this.energy=0;this.levelSamples=0;}if(this.length>=sampleRate*2)this.flush();}return true;}
}
registerProcessor('pcm-capture',CaptureProcessor);
