import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { api } from '../lib/api';
import type { Route, Ticket } from '../lib/types';
function useConsoleState(){
  const [routes,setRoutes] = useState<Route[]>([]), [tickets,setTickets] = useState<Ticket[]>([]);
  const [error,setError] = useState(''), [loading,setLoading] = useState(true), [busy,setBusy] = useState(false);
  const [refreshRevision,setRefreshRevision] = useState(0);
  const [online,setOnline] = useState(navigator.onLine);
  const refresh = useCallback(async()=>{
    setLoading(true); setError('');
    try {const [r,t] = await Promise.all([api.routes(),api.tickets()]); setRoutes(r);setTickets(t);setRefreshRevision(v=>v+1);}
    catch(e){setError((e as Error).message);} finally{setLoading(false);}
  },[]);
  useEffect(()=>{void refresh(); const update=()=>setOnline(navigator.onLine); window.addEventListener('online',update);window.addEventListener('offline',update);return()=>{window.removeEventListener('online',update);window.removeEventListener('offline',update);};},[refresh]);
  async function mutate(work:()=>Promise<Ticket>):Promise<Ticket|null>{
    setBusy(true);setError('');
    try {const ticket=await work();setTickets(list=>[ticket,...list.filter(t=>t.id!==ticket.id)]);return ticket;}
    catch(e){setError((e as Error).message);return null;}finally{setBusy(false);}
  }
  return {refreshRevision,routes,tickets,error,setError,loading,busy,online,refresh,mutate};
}
const Context = createContext<ReturnType<typeof useConsoleState>|null>(null);
export function ConsoleProvider({children}:{children:ReactNode}){const value=useConsoleState();return <Context.Provider value={value}>{children}</Context.Provider>;}
export function useConsole(){const value=useContext(Context);if(!value)throw new Error('ConsoleProvider missing');return value;}
