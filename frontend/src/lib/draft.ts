import type { Draft } from './types';
export const DRAFT_KEY = 'bolbus.draft.v1';
export function readDraft(): Draft | null {
  try {
    const value = JSON.parse(localStorage.getItem(DRAFT_KEY) ?? 'null');
    if (!value || typeof value.client_request_id !== 'string' || !Number.isInteger(value.route_id) || !Number.isInteger(value.passenger_count) || value.passenger_count < 1 || value.passenger_count > 20 || !['standard','demo-concession','shakti-demo'].includes(value.category) || !['en-IN','kn-IN','hi-IN'].includes(value.language) || ![value.origin_stop_id,value.destination_stop_id].every(x=>x===null || Number.isInteger(x))) return null;
    return value;
  } catch {return null;}
}
