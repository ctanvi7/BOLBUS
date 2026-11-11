import { describe,it,expect,vi,afterEach } from 'vitest';
import { render,screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ConsoleProvider } from './state/ConsoleContext';
import { App } from './App';
import { captureAudio,encodeWav } from './lib/audio';
vi.mock('./lib/audio',async original=>({...await original<typeof import('./lib/audio')>(),captureAudio:vi.fn()}));
const result={route_id:1,provider:'manual-text',is_fixture:false,confidence:null,original_transcription:'Two tickets to Lake',items:[{destination:'Lake',destination_stop_id:2,quantity:2,category:null,unresolved:['Choose a category'],candidates:[]}]};
function server(live=false){
 return vi.spyOn(globalThis,'fetch').mockImplementation(async input=>{const url=String(input);
 if(url.endsWith('/routes'))return new Response(JSON.stringify([{id:1,code:'DEMO-01',name:'Demo',stops:[{id:1,name:'Central',name_kn:'ಕೇಂದ್ರ',name_hi:'केंद्र',position:0},{id:2,name:'Lake',name_kn:'ಕೆರೆ',name_hi:'झील',position:1}],fare_rules:[{category:'standard',label:'Standard demo'}],service_types:['ordinary']}]));
 if(url.endsWith('/ticket-requests'))return new Response('[]');
 if(url.endsWith('/speech/status'))return new Response(JSON.stringify({mode:live?'gnani':'disabled',live_available:live,fixtures:[],max_seconds:30}));
 return new Response(JSON.stringify(result));});
}
function mount(){return render(<MemoryRouter initialEntries={['/voice']}><ConsoleProvider><App/></ConsoleProvider></MemoryRouter>);}
afterEach(()=>{vi.restoreAllMocks();sessionStorage.clear();});
describe('speech review',()=>{
 it('keeps manual fallback usable when speech is disabled and requires explicit category',async()=>{server();const user=userEvent.setup();mount();await screen.findByText('Live speech unavailable · use manual text below');
 expect(screen.getByRole('button',{name:'● Record ticket request'})).toBeDisabled();await user.type(screen.getByLabelText('Transcription / manual text'),'Two tickets to Lake');await user.click(screen.getByRole('button',{name:'Extract / recheck edited text'}));
 await screen.findByText('Editable ticket drafts');expect(screen.getByRole('button',{name:'Save reviewed draft →'})).toBeDisabled();
 await user.selectOptions(screen.getByLabelText('Boarding stop'),'1');await user.selectOptions(screen.getByLabelText('Category for request 1'),'standard');expect(screen.getByRole('button',{name:'Save reviewed draft →'})).toBeEnabled();
 await user.type(screen.getByLabelText('Transcription / manual text'),' correction');expect(screen.getByRole('button',{name:'Save reviewed draft →'})).toBeDisabled();});
 it('stops microphone capture on navigation',async()=>{server(true);const cancel=vi.fn();vi.mocked(captureAudio).mockResolvedValue({cancel,stop:vi.fn()});Object.defineProperty(navigator,'mediaDevices',{value:{getUserMedia:vi.fn()},configurable:true});const user=userEvent.setup();const view=mount();await screen.findByText('Gnani configured · live service not yet verified on this device');await user.click(screen.getByRole('button',{name:'● Record ticket request'}));await screen.findByRole('button',{name:'Stop recording & transcribe'});view.unmount();expect(cancel).toHaveBeenCalled();});
 it('shows microphone denial and preserves text fallback',async()=>{server(true);vi.mocked(captureAudio).mockRejectedValue(new Error('Permission denied'));const user=userEvent.setup();mount();await screen.findByText('Gnani configured · live service not yet verified on this device');await user.click(screen.getByRole('button',{name:'● Record ticket request'}));expect(await screen.findByRole('alert')).toHaveTextContent('permission denied');expect(screen.getByLabelText('Transcription / manual text')).toBeEnabled();});
 it('encodes a true mono PCM16 WAV with actual sample rate',async()=>{const blob=encodeWav([new Float32Array([-1,0,1])],48000);const buffer=await new Promise<ArrayBuffer>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result as ArrayBuffer);reader.onerror=reject;reader.readAsArrayBuffer(blob);});const view=new DataView(buffer);expect(view.getUint16(22,true)).toBe(1);expect(view.getUint32(24,true)).toBe(48000);expect(view.getUint16(34,true)).toBe(16);expect(view.getUint32(40,true)).toBe(6);expect(view.getInt16(44,true)).toBe(-32768);expect(view.getInt16(48,true)).toBe(32767);});
});
