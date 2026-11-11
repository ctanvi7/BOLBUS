import type { Draft, Fields, Route, Ticket } from './types';
const base = import.meta.env.VITE_API_BASE_URL ?? '';
export async function request<T>(path:string, method='GET', body?:unknown):Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(()=>controller.abort(), 10000);
  try {
    const response = await fetch(`${base}/api${path}`,{method, signal:controller.signal, headers:{'Content-Type':'application/json'}, ...(body === undefined ? {} : {body:JSON.stringify(body)})});
    if (!response.ok) {
      const payload = await response.json().catch(()=>null);
      throw new Error(typeof payload?.detail === 'string' ? payload.detail : `Request failed (${response.status}). Check the fields and retry.`);
    }
    return await response.json() as T;
  } catch(error) {
    if(error instanceof TypeError || (error instanceof DOMException && error.name === 'AbortError')) throw new Error('Server unreachable or timed out. Your local draft is retained. Refresh requests before retrying an uncertain action.');
    throw error;
  } finally {clearTimeout(timeout);}
}
export const api = {
  routes:()=>request<Route[]>('/routes'), async tickets():Promise<Ticket[]> {
    const all:Ticket[]=[];let offset=0;
    while(true){const page=await request<Ticket[]>(offset===0?'/ticket-requests':`/ticket-requests?limit=100&offset=${offset}`);all.push(...page);if(page.length<100)return [...new Map(all.map(t=>[t.id,t])).values()];offset+=page.length;}
  },
  create:(data:Draft)=>request<Ticket>('/ticket-requests','POST',data),
  edit:(id:string,fields:Fields,version:number)=>request<Ticket>(`/ticket-requests/${id}`,'PUT',{...fields,version}),
  action:(id:string,action:string,body:object)=>request<Ticket>(`/ticket-requests/${id}/${action}`,'POST',body),
};

export const speechApi = {
 status:()=>request<import('./types').SpeechStatus>('/speech/status'),
 parse:(route_id:number,text:string)=>request<import('./types').SpeechResult>('/speech/parse','POST',{route_id,text}),
 fixture:(route_id:number,name:string)=>request<import('./types').SpeechResult>(`/speech/fixture/${encodeURIComponent(name)}?route_id=${route_id}`,'POST'),
 async transcribe(route:number,language:string,audio:Blob):Promise<import('./types').SpeechResult>{
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),60000);
  try{
   const response=await fetch(`${base}/api/speech/transcribe?route_id=${route}&language=${encodeURIComponent(language)}`,{method:'POST',headers:{'Content-Type':'audio/wav'},body:audio,signal:controller.signal});
   const data=await response.json().catch(()=>null);
   if(!response.ok)throw new Error(typeof data?.detail==='string'?data.detail:'Speech request failed. Retry or use manual text.');
   return data;
  }catch(e){if(e instanceof TypeError||(e instanceof DOMException&&e.name==='AbortError'))throw new Error('Speech connection failed or timed out. Use manual text or retry.');throw e;}
  finally{clearTimeout(timer);}
 }
};

export const batchApi={
 list:()=>request<import('./types').TicketBatch[]>('/batches'),
 get:(id:string)=>request<import('./types').TicketBatch>(`/batches/${id}`),
 create:(data:object)=>request<import('./types').TicketBatch>('/batches','POST',data),
 edit:(batch:string,item:string,version:number,draft:import('./types').BatchDraft)=>request<import('./types').TicketBatch>(`/batches/${batch}/items/${item}`,'PUT',{version,draft}),
 cancel:(batch:string,item:string,version:number)=>request<import('./types').TicketBatch>(`/batches/${batch}/items/${item}/cancel`,'POST',{version}),
 prepare:(batch:string,versions:Record<string,number>)=>request<{batch:import('./types').TicketBatch;processing_ms:number;results:{item_id:string;ok:boolean;error?:string}[]}>(`/batches/${batch}/prepare`,'POST',{versions}),
};
