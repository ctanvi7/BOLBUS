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
  routes:()=>request<Route[]>('/routes'), tickets:()=>request<Ticket[]>('/ticket-requests'),
  create:(data:Draft)=>request<Ticket>('/ticket-requests','POST',data),
  edit:(id:string,fields:Fields,version:number)=>request<Ticket>(`/ticket-requests/${id}`,'PUT',{...fields,version}),
  action:(id:string,action:string,body:object)=>request<Ticket>(`/ticket-requests/${id}/${action}`,'POST',body),
};
