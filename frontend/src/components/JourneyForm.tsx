import type { Fields, Route } from '../lib/types';
export function JourneyForm({value,onChange,routes,disabled=false}:{value:Fields;onChange:(v:Fields)=>void;routes:Route[];disabled?:boolean}){
 const route=routes.find(r=>r.id===value.route_id);
 const stopName=(stop:NonNullable<typeof route>['stops'][number])=>value.language==='kn-IN'?stop.name_kn:value.language==='hi-IN'?stop.name_hi:stop.name;
 return <fieldset disabled={disabled} className="grid gap-4 sm:grid-cols-2">
  <label className="sm:col-span-2">Demo route<select value={value.route_id} onChange={e=>onChange({...value,route_id:Number(e.target.value),origin_stop_id:null,destination_stop_id:null})}>{routes.map(r=><option key={r.id} value={r.id}>{r.code} · {r.name}</option>)}</select></label>
  <label>Stop display language<select value={value.language} onChange={e=>onChange({...value,language:e.target.value as Fields['language']})}><option value="en-IN">English</option><option value="kn-IN">ಕನ್ನಡ</option><option value="hi-IN">हिन्दी</option></select></label>
  <label>Passengers<input type="number" min="1" max="20" required value={value.passenger_count} onChange={e=>onChange({...value,passenger_count:Number(e.target.value)})}/></label>
  {(['origin_stop_id','destination_stop_id'] as const).map((key,index)=><label key={key}>{index===0?'Boarding stop':'Destination'}<select value={value[key]??''} onChange={e=>onChange({...value,[key]:e.target.value?Number(e.target.value):null})}><option value="">Choose stop</option>{route?.stops.map(s=><option key={s.id} value={s.id}>{stopName(s)}</option>)}</select></label>)}
  <label className="sm:col-span-2">Fare category<select value={value.category} onChange={e=>onChange({...value,category:e.target.value as Fields['category']})}>{route?.fare_rules.map(r=><option key={r.category} value={r.category}>{r.label}</option>)}</select></label>
 </fieldset>;
}
