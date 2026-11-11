// Browser recovery never replays payment, verification or approval actions.
export function recoveryRead<T>(key:string):T|null{try{return JSON.parse(localStorage.getItem(key)??'null');}catch{return null;}}
export function recoveryWrite(key:string,value:unknown){localStorage.setItem(key,JSON.stringify(value));}
export function batchCreationKey(payload:object,intent:string):string{
 const serialized=JSON.stringify(payload), saved=recoveryRead<{payload:string;id:string}>(`bolbus.batch-intent.${intent}`);
 if(saved?.payload===serialized)return saved.id;
 if(saved)throw new Error('A save was already attempted for this extraction with different details. Check the pending queue before starting a new extraction.');
 const id=crypto.randomUUID();recoveryWrite(`bolbus.batch-intent.${intent}`,{payload:serialized,id});return id;
}
