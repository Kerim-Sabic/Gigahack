export type Ack = {acknowledged_samples:number;sample_rate:number};
export class CaptureQueue {
 private pending:{sequence:number;data:ArrayBuffer}[]=[];
 private running:Promise<void>|null=null;
 nextSequence=0;pendingSamples=0;error:Error|null=null;
 constructor(private rate:number,private send:(sequence:number,data:ArrayBuffer)=>Promise<Ack>,private ack:(value:Ack)=>void,private failed:(error:Error)=>void){}
 enqueue(data:ArrayBuffer){const samples=data.byteLength/2;if(this.pendingSamples+samples>this.rate*60)throw new Error('Recording stopped: more than 60 seconds could not be saved.');this.pending.push({sequence:this.nextSequence++,data});this.pendingSamples+=samples;if(!this.error)void this.drain();}
 async drain():Promise<void>{if(this.running)return this.running;this.running=(async()=>{while(this.pending.length){const item=this.pending[0];let result:Ack|undefined;for(let attempt=0;attempt<3;attempt++){try{result=await this.send(item.sequence,item.data);break;}catch(e){if(attempt===2){this.error=e instanceof Error?e:new Error(String(e));this.failed(this.error);return;}}}if(!result)return;this.pending.shift();this.pendingSamples-=item.data.byteLength/2;this.ack(result);}})().finally(()=>{this.running=null;});return this.running;}
 async retry(){this.error=null;await this.drain();if(this.error)throw this.error;}
 async finish(){await this.drain();if(this.error)throw this.error;if(this.pending.length)throw new Error('Audio is not fully acknowledged.');}
}
