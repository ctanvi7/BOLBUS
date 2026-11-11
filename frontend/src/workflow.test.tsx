import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ConsoleProvider } from './state/ConsoleContext';
import { App } from './App';
import { readDraft, DRAFT_KEY } from './lib/draft';
import { api } from './lib/api';
import type { Ticket } from './lib/types';
const route={id:1,code:'DEMO-01',name:'Fictional training route',is_demo:true,stops:[{id:1,position:0,name:'Central',name_kn:'ಕೇಂದ್ರ',name_hi:'केंद्र'},{id:2,position:1,name:'Lake',name_kn:'ಕೆರೆ',name_hi:'झील'}],fare_rules:[{category:'standard',label:'Standard demo',per_stage_paise:500,verification_required:false,source:'Invented demo'}]};
const draft={route_id:1,origin_stop_id:1,destination_stop_id:2,passenger_count:1,category:'standard',language:'en-IN',client_request_id:'8df22e79-a9b8-48b5-a4be-285844143c6b'};
function mockServer(){
 let ticket:Ticket={...draft,category:'standard',language:'en-IN',id:'ticket-1',state:'draft',payment_collected:false,concession_verified:false,total_paise:null,approved_by:null,approved_at:null,created_at:new Date().toISOString(),version:1,issues:[]};
 return vi.spyOn(globalThis,'fetch').mockImplementation(async (input,init)=>{
  const url=String(input); const body=JSON.parse(String(init?.body??'{}'));
  if(url.endsWith('/routes'))return new Response(JSON.stringify([route]));
  if(url.endsWith('/ticket-requests')&&init?.method==='GET')return new Response('[]');
  if(url.endsWith('/validate'))ticket={...ticket,state:'pending-verification',total_paise:500,issues:['Confirm payment'],version:2};
  if(url.endsWith('/verify'))ticket={...ticket,state:'ready-for-approval',payment_collected:body.payment_collected,issues:[],version:3};
  if(url.endsWith('/approve'))ticket={...ticket,state:'approved',approved_by:body.conductor_name,approved_at:new Date().toISOString(),version:4};
  return new Response(JSON.stringify(ticket));
 });
}
describe('conductor workflow',()=>{
 it('requires verification and explicit confirmation before approval',async()=>{
  localStorage.clear();const fetch=mockServer(); const user=userEvent.setup();
  render(<MemoryRouter><ConsoleProvider><App/></ConsoleProvider></MemoryRouter>);
  await screen.findByLabelText('Boarding stop');
  await user.selectOptions(screen.getByLabelText('Boarding stop'),'1');await user.click(screen.getByRole('button',{name:/Lake/}));
  await user.click(screen.getByRole('button',{name:/Continue to fare & approval/}));
  const approve=await screen.findByRole('button',{name:'Approve demo request'});expect(approve).toBeDisabled();
  await user.click(screen.getByRole('button',{name:'Validate request'}));
  await user.click(await screen.findByLabelText('I collected payment'));
  await user.click(screen.getByRole('button',{name:'Save verification'}));
  await waitFor(()=>expect(screen.getByText('ready for approval')).toBeInTheDocument());
  await user.type(screen.getByLabelText('Conductor name'),'Tanvi');expect(approve).toBeDisabled();
  await user.click(screen.getByLabelText('I approve this demo request'));expect(approve).toBeEnabled();
  await user.click(approve);await screen.findByText('Demo request approved');expect(screen.getByText('This is not a valid travel ticket.')).toBeInTheDocument();fetch.mockRestore();
 });
 it('retains local drafts on network failure and displays an error',async()=>{
  localStorage.setItem(DRAFT_KEY,JSON.stringify(draft));const fetch=mockServer();const user=userEvent.setup();
  render(<MemoryRouter><ConsoleProvider><App/></ConsoleProvider></MemoryRouter>);await screen.findByLabelText('Boarding stop');
  fetch.mockRejectedValue(new TypeError('network'));await user.click(screen.getByRole('button',{name:/Continue to fare & approval/}));
  expect(await screen.findByRole('alert')).toHaveTextContent('Server unreachable');expect(readDraft()?.client_request_id).toBe(draft.client_request_id);fetch.mockRestore();
 });
 it('rejects corrupt draft data',()=>{localStorage.setItem(DRAFT_KEY,'bad json');expect(readDraft()).toBeNull();localStorage.setItem(DRAFT_KEY,JSON.stringify({...draft,passenger_count:0}));expect(readDraft()).toBeNull();});
 it('reports API conflict messages',async()=>{const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify({detail:'Request changed'}),{status:409}));await expect(api.action('x','cancel',{version:1})).rejects.toThrow('Request changed');fetch.mockRestore();});
});
