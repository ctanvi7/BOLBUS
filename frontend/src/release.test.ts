import {afterEach,expect,it,vi} from 'vitest';
import {api} from './lib/api';
afterEach(()=>vi.restoreAllMocks());
it('loads unfinished tickets older than the first listing page',async()=>{
 const first=Array.from({length:100},(_,i)=>({id:String(i),state:'approved'}));
 const fetch=vi.spyOn(globalThis,'fetch').mockImplementation(async input=>new Response(JSON.stringify(String(input).includes('offset=100')?[{id:'old-pending',state:'pending-verification'}]:first)));
 const tickets=await api.tickets();expect(tickets).toHaveLength(101);expect(tickets.at(-1)?.id).toBe('old-pending');expect(fetch).toHaveBeenCalledTimes(2);
});
it('does not silently return a partial queue if a later page fails',async()=>{
 vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(new Response(JSON.stringify(Array.from({length:100},(_,i)=>({id:String(i)}))))).mockRejectedValueOnce(new TypeError('offline'));
 await expect(api.tickets()).rejects.toThrow('Server unreachable');
});
