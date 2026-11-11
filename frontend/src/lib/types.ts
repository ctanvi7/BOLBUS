export type State = 'draft' | 'needs-clarification' | 'pending-verification' | 'ready-for-approval' | 'approved' | 'cancelled';
export type Language = 'en-IN' | 'kn-IN' | 'hi-IN';
export interface Stop {id:number; position:number; name:string; name_kn:string; name_hi:string}
export interface FareRule {category:Fields['category']; label:string; per_stage_paise:number; verification_required:boolean; source:string}
export interface Route {service_types?:string[];id:number; code:string; name:string; is_demo:boolean; stops:Stop[]; fare_rules:FareRule[]}
export interface Fields {service_type?:string; origin_text?:string|null; destination_text?:string|null; route_id:number; origin_stop_id:number|null; destination_stop_id:number|null; passenger_count:number; category:'standard'|'demo-concession'|'shakti-demo'; language:Language}
export interface Draft extends Fields {client_request_id:string}
export interface Ticket extends Fields {batch_id?:string|null;id:string; client_request_id:string; state:State; concession_verified:boolean; payment_collected:boolean; total_paise:number|null; approved_by:string|null; approved_at:string|null; created_at:string; version:number; issues:string[]; documents_verified?:boolean; quote_snapshot?:string|null}
export const money = (paise:number|null) => paise === null ? '—' : new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format(paise/100);
export interface SpeechItem {client_request_id?:string;prepared_request_id?:string;destination:string;destination_stop_id:number|null;quantity:number|null;category:string|null;unresolved:string[];candidates:{id:number;name:string}[]}
export interface SpeechResult {batch_intent_id?:string;saved_batch_id?:string;route_id?:number;original_transcription:string;items:SpeechItem[];provider:string;is_fixture:boolean;confidence:null}
export interface SpeechStatus {mode:'disabled'|'fixture'|'gnani';live_available:boolean;fixtures:string[];max_seconds:number}
export interface BatchDraft {origin_stop_id:number|null;destination_stop_id:number|null;destination_text:string;quantity:number|null;category:string|null;service_type:string;language:Language}
export interface BatchItem {id:string;position:number;version:number;draft:BatchDraft;ticket:Ticket|null;state:State;issues:string[];last_error:string|null;alternatives:{id:number;name:string}[]}
export interface TicketBatch {id:string;route_id:number;original_transcription:string;source:string;created_at:string;items:BatchItem[]}
