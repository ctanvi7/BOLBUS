export function encodeWav(chunks:Float32Array[],rate:number):Blob {
 const length=chunks.reduce((n,c)=>n+c.length,0), buffer=new ArrayBuffer(44+length*2), view=new DataView(buffer);
 const string=(offset:number,text:string)=>[...text].forEach((c,i)=>view.setUint8(offset+i,c.charCodeAt(0)));
 string(0,'RIFF');view.setUint32(4,36+length*2,true);string(8,'WAVE');string(12,'fmt ');
 view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,rate,true);
 view.setUint32(28,rate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);string(36,'data');view.setUint32(40,length*2,true);
 let offset=44;for(const chunk of chunks)for(const sample of chunk){const value=Math.max(-1,Math.min(1,sample));view.setInt16(offset,value<0?value*32768:value*32767,true);offset+=2;}
 return new Blob([buffer],{type:'audio/wav'});
}
export async function captureAudio(onLimit:()=>void){
 const stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true},video:false});
 let context:AudioContext|undefined, node:AudioWorkletNode|undefined, source:MediaStreamAudioSourceNode|undefined;
 let timer:ReturnType<typeof setTimeout>|undefined;const chunks:Float32Array[]=[];
 const cleanup=()=>{clearTimeout(timer);stream.getTracks().forEach(t=>t.stop());source?.disconnect();node?.disconnect();if(context&&context.state!=='closed')void context.close();};
 try{
  context=new AudioContext();await context.audioWorklet.addModule('/pcm-recorder.js');await context.resume();
  source=context.createMediaStreamSource(stream);node=new AudioWorkletNode(context,'pcm-recorder');const rate=context.sampleRate;let samples=0;
  node.port.onmessage=e=>{const remaining=rate*29-samples;if(remaining>0){const chunk=(e.data as Float32Array).slice(0,remaining);chunks.push(chunk);samples+=chunk.length;}};
  source.connect(node);node.connect(context.destination);timer=setTimeout(onLimit,29000);
  return {stop:()=>{cleanup();return encodeWav(chunks,rate);},cancel:cleanup};
 }catch(e){cleanup();throw e;}
}
