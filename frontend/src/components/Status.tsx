import type { State } from '../lib/types';
export function Status({state}:{state:State}){return <span className={`status ${state==='approved'?'bg-lime':state==='cancelled'?'bg-slate-200':'bg-orange/20'}`}>{state.replaceAll('-',' ')}</span>;}
