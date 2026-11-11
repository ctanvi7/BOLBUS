import { Link } from 'react-router-dom';
import { useState } from 'react';
import { useConsole } from '../state/ConsoleContext';
import { Status } from '../components/Status';
import { money } from '../lib/types';
export function Requests(){const {tickets}=useConsole();const [filter,setFilter]=useState('all'); const visible=tickets.filter(t=>filter==='all'||t.state===filter);
 return <section className="panel"><div className="flex flex-wrap justify-between items-center gap-4"><div><div className="eyebrow">REQUEST REGISTER</div><h1>Ticket requests</h1></div><label>Filter<select value={filter} onChange={e=>setFilter(e.target.value)}>{['all','draft','needs-clarification','pending-verification','ready-for-approval','approved','cancelled'].map(s=><option key={s}>{s}</option>)}</select></label></div><p className="muted mb-4">Latest 100 saved requests. Approval records are demonstration records.</p>
 {visible.length===0?<p className="py-12 text-center">No requests here yet. <Link className="underline" to="/">Create a request</Link></p>:<div className="space-y-3">{visible.map(t=><Link to={`/requests/${t.id}`} key={t.id} className="flex flex-wrap gap-4 items-center justify-between rounded-xl border p-4 hover:bg-cloud"><div><strong>#{t.id.slice(0,8)}</strong><p className="muted">{t.passenger_count} passenger(s) · {new Date(t.created_at).toLocaleString()}</p></div><Status state={t.state}/><strong>{money(t.total_paise)} →</strong></Link>)}</div>}</section>;
}
