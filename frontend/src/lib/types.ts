export type State = 'draft' | 'needs-clarification' | 'pending-verification' | 'ready-for-approval' | 'approved' | 'cancelled';
export type Language = 'en-IN' | 'kn-IN' | 'hi-IN';
export interface Stop {id:number; position:number; name:string; name_kn:string; name_hi:string}
export interface FareRule {category:Fields['category']; label:string; per_stage_paise:number; verification_required:boolean; source:string}
export interface Route {service_types?:string[];id:number; code:string; name:string; is_demo:boolean; stops:Stop[]; fare_rules:FareRule[]}
export interface Fields {service_type?:string; origin_text?:string|null; destination_text?:string|null; route_id:number; origin_stop_id:number|null; destination_stop_id:number|null; passenger_count:number; category:'standard'|'demo-concession'|'shakti-demo'; language:Language}
export interface Draft extends Fields {client_request_id:string}
export interface Ticket extends Fields {id:string; client_request_id:string; state:State; concession_verified:boolean; payment_collected:boolean; total_paise:number|null; approved_by:string|null; approved_at:string|null; created_at:string; version:number; issues:string[]; documents_verified?:boolean; quote_snapshot?:string|null}
export const money = (paise:number|null) => paise === null ? '—' : new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format(paise/100);
