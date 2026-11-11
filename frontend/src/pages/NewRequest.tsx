import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { JourneyForm } from '../components/JourneyForm';
import { api } from '../lib/api';
import { DRAFT_KEY, readDraft } from '../lib/draft';
import type { Draft } from '../lib/types';
import { useConsole } from '../state/ConsoleContext';
export function NewRequest(){
 const {routes,busy,online,mutate}=useConsole(); const navigate=useNavigate();
 const [draft,setDraft]=useState<Draft|null>(readDraft); const [storageError,setStorageError]=useState(false);
 useEffect(()=>{if(!draft&&routes.length)setDraft({client_request_id:crypto.randomUUID(),route_id:routes[0].id,origin_stop_id:null,destination_stop_id:null,passenger_count:1,category:'standard',language:'en-IN'});},[draft,routes]);
 useEffect(()=>{if(draft)try{localStorage.setItem(DRAFT_KEY,JSON.stringify(draft));}catch{setStorageError(true);}},[draft]);
 if(!draft||!routes.length)return <p className="panel">Connect to the local server to load demo routes.</p>;
 return <div className="grid gap-6 lg:grid-cols-[1fr_300px]"><section className="panel"><div className="eyebrow">CONDUCTOR WORKSPACE</div><h1>New ticket request</h1><p className="muted mb-6">Set the journey. Check the details. You decide when to approve.</p>
 {storageError&&<p role="alert">Local storage is unavailable. Keep this tab open to retain your draft.</p>}
 <form onSubmit={async e=>{e.preventDefault();const result=await mutate(()=>api.create(draft));if(result){try{localStorage.removeItem(DRAFT_KEY);}catch{}setDraft({...draft,client_request_id:crypto.randomUUID()});navigate(`/requests/${result.id}`);}}}>
 <JourneyForm value={draft} onChange={v=>setDraft({...v,client_request_id:crypto.randomUUID()})} routes={routes} disabled={busy}/>
 <button className="primary mt-6 w-full" disabled={busy||!online}>{busy?'Saving…':'Save draft & review →'}</button></form></section>
 <aside className="space-y-5"><section className="panel bg-navy text-cloud"><span className="text-lime text-3xl" aria-hidden="true">◉</span><h2 className="mt-4">Voice comes next.</h2><p className="text-white/75">Use manual entry in this foundation. Speech recognition and AI interpretation are not connected.</p><p className="mt-4 text-sm text-lime">English · ಕನ್ನಡ · हिन्दी stop labels</p></section><section className="panel"><h2>Conductor in control</h2><ol className="space-y-3 text-sm mt-3"><li>01 · Validate journey and demo fare</li><li>02 · Check eligibility and collect payment</li><li>03 · Explicitly approve the demo request</li></ol><p className="muted mt-4">No real ticket is printed or issued.</p></section></aside></div>;
}
