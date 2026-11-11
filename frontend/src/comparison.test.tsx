import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { App } from './App';
import { ConsoleProvider } from './state/ConsoleContext';

const route={id:1,code:'DEMO-01',name:'Fictional training corridor',is_demo:true,service_types:['ordinary'],stops:[{id:1,position:0,name:'Central',name_kn:'ಕೇಂದ್ರ',name_hi:'केंद्र'},{id:2,position:1,name:'Market',name_kn:'ಮಾರುಕಟ್ಟೆ',name_hi:'बाज़ार'},{id:5,position:4,name:'Lake',name_kn:'ಕೆರೆ',name_hi:'झील'}],fare_rules:[{category:'standard',label:'Standard demo',per_stage_paise:500,verification_required:false,source:'Synthetic training data'}]};
function setup(){
 let ticket:any=null;let revision=0;
 const fetch=vi.spyOn(globalThis,'fetch').mockImplementation(async(input,init)=>{
  const url=String(input),method=init?.method??'GET';
  if(url.endsWith('/routes'))return new Response(JSON.stringify([route]));
  if(url.endsWith('/ticket-requests')&&method==='GET')return new Response(JSON.stringify(ticket?[ticket]:[]));
  if(url.endsWith('/speech/status'))return new Response(JSON.stringify({mode:'disabled',live_available:false,fixtures:[],max_seconds:29}));
  if(url.endsWith('/speech/parse'))return new Response(JSON.stringify({route_id:1,original_transcription:'Two standard tickets to Lake',provider:'deterministic-v1',is_fixture:false,confidence:null,items:[{destination:'Lake',destination_stop_id:5,quantity:2,category:'standard',unresolved:[],candidates:[]}]}));
  const body=JSON.parse(String(init?.body??'{}'));
  if(url.endsWith('/ticket-requests')&&method==='POST'){ticket={...body,id:`ticket-${++revision}`,state:'draft',version:1,issues:[],total_paise:null,payment_collected:false,concession_verified:false,documents_verified:false,approved_by:null,approved_at:null,created_at:new Date().toISOString()};return new Response(JSON.stringify(ticket),{status:201});}
  if(url.includes('/ticket-requests/')&&method==='GET')return new Response(JSON.stringify(ticket));
  if(url.endsWith('/validate'))ticket={...ticket,state:'pending-verification',total_paise:4000,issues:['Conductor must confirm payment collection.'],version:ticket.version+1};
  if(url.endsWith('/verify'))ticket={...ticket,state:'ready-for-approval',payment_collected:body.payment_collected,version:ticket.version+1,issues:[]};
  if(url.endsWith('/approve'))ticket={...ticket,state:'approved',approved_by:body.conductor_name,approved_at:new Date().toISOString(),version:ticket.version+1};
  return new Response(JSON.stringify(ticket));
 });
 return fetch;
}
function mount(){return render(<MemoryRouter initialEntries={['/compare']}><ConsoleProvider><App/></ConsoleProvider></MemoryRouter>);}
async function finishActiveTicket(user:ReturnType<typeof userEvent.setup>){
 await user.click(await screen.findByRole('button',{name:'Validate route and fare →'}));
 await user.click(await screen.findByLabelText('I collected the demo payment'));
 await user.click(screen.getByRole('button',{name:'Save verification →'}));
 await user.type(await screen.findByLabelText('Comparison conductor name'),'Demo conductor');
 await user.click(screen.getByLabelText('Explicit comparison approval'));
 await user.click(screen.getByRole('button',{name:'Approve simulated ticket'}));
}
afterEach(()=>{vi.restoreAllMocks();localStorage.clear();});
describe('prototype comparison flow',()=>{
 it('completes equivalent manual and transcript-assisted tickets and records only observed measurements',async()=>{
  setup();const user=userEvent.setup();mount();
  expect(await screen.findByText(/not BMTC deployment results/)).toBeInTheDocument();
  await user.click(screen.getByRole('button',{name:'Start manual attempt →'}));
  await user.selectOptions(screen.getByLabelText('Attempt boarding'),'1');
  await user.selectOptions(screen.getByLabelText('Attempt destination'),'5');
  await user.type(screen.getByLabelText('Attempt passengers'),'2');
  await user.selectOptions(screen.getByLabelText('Attempt category'),'standard');
  await user.click(screen.getByRole('button',{name:'Save manual ticket draft →'}));
  await finishActiveTicket(user);
  await screen.findByText('Observed task results');
  await user.click(screen.getByRole('button',{name:'Start BOLBUS attempt →'}));
  await user.type(screen.getByLabelText('Spoken request transcript'),'Two standard tickets to Lake');
  await user.click(screen.getByRole('button',{name:'Extract ticket details'}));
  await user.selectOptions(await screen.findByLabelText('Assisted boarding'),'1');
  const assistedDestination=screen.getByLabelText('Assisted destination');await user.selectOptions(assistedDestination,'2');await user.tab();await user.selectOptions(assistedDestination,'5');
  await user.click(screen.getByRole('button',{name:'Save reviewed ticket draft →'}));
  await finishActiveTicket(user);
  await waitFor(()=>expect(screen.getByText('Observed task results')).toBeInTheDocument());
  const rows=screen.getAllByRole('row');expect(rows).toHaveLength(3);
  expect(rows[1]).toHaveTextContent('A · Manual');expect(rows[1]).not.toHaveTextContent('Not run');
  expect(rows[2]).toHaveTextContent('B · BOLBUS');expect(rows[2]).not.toHaveTextContent('Not run');
  expect(rows[2]).toHaveTextContent('2');
 });
 it('requires explicit category after transcript extraction when speech omits it',async()=>{
  setup();vi.spyOn(globalThis,'fetch').mockImplementation(async(input,init)=>{if(String(input).endsWith('/speech/parse'))return new Response(JSON.stringify({route_id:1,original_transcription:'Two tickets to Lake',provider:'deterministic-v1',is_fixture:false,confidence:null,items:[{destination:'Lake',destination_stop_id:5,quantity:2,category:null,unresolved:['Choose a category; none was reliably stated.'],candidates:[]}]}));return new Response(JSON.stringify([route]));});
  const user=userEvent.setup();mount();await user.click(await screen.findByRole('button',{name:'Start BOLBUS attempt →'}));await user.type(screen.getByLabelText('Spoken request transcript'),'Two tickets to Lake');await user.click(screen.getByRole('button',{name:'Extract ticket details'}));expect(await screen.findByLabelText('Assisted category')).toHaveValue('');expect(screen.getByRole('button',{name:'Save reviewed ticket draft →'})).toBeDisabled();
 });
});
