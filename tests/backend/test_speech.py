import asyncio
import io
import wave
import httpx
import pytest
from fastapi import HTTPException
from app.config import settings
from app.models import Stop, StopAlias
from app.services.speech.parser import parse
from app.services.speech.provider import GnaniProvider, validate_audio, get_provider
from app.main import app
from test_engine import database


def wav_bytes():
    buffer=io.BytesIO()
    with wave.open(buffer,'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000); wav.writeframes(b'\0\0'*3200)
    return buffer.getvalue()


@pytest.fixture
def speech_route(client):
    with database() as db:
        for index, names in enumerate([('Central','ಕೇಂದ್ರ','केंद्र'),('Majestic','ಮೆಜೆಸ್ಟಿಕ್','मैजेस्टिक'),('Silk Board','ಸಿಲ್ಕ್ ಬೋರ್ಡ್','सिल्क बोर्ड'),('Jayanagar','ಜಯನಗರ','जयनगर'),('BTM','ಬಿಟಿಎಂ','बीटीएम')],1):
            stop=db.get(Stop,index)
            stop.name, stop.name_kn, stop.name_hi=names
        db.commit()
    return client


@pytest.mark.parametrize('text,quantity,destination',[
    ('Majestic ge eradu ticket',2,'majestic'),('Two tickets to Silk Board',2,'silk board'),
    ('Jayanagar ke teen ticket',3,'jayanagar'),('ಎರಡು ಟಿಕೆಟ್ ಜಯನಗರ',2,'ಜಯನಗರ'),('ಮೆಜೆಸ್ಟಿಕ್‌ಗೆ ಎರಡು ಟಿಕೆಟ್',2,'ಮೆಜೆಸ್ಟಿಕ್'),
    ('तीन टिकट जयनगर',3,'जयनगर'),('२ टिकट जयनगर',2,'जयनगर'),
    ('two standard tickets to Majestic',2,'majestic'),
])
def test_multilingual_parser(speech_route,text,quantity,destination):
    result=speech_route.post('/api/speech/parse',json={'route_id':1,'text':text}).json()
    assert result['original_transcription']==text and result['provider']=='manual-text'
    item=result['items'][0]
    assert item['quantity']==quantity and item['destination']==destination and item['destination_stop_id'] is not None
    assert item['category']==('standard' if 'standard' in text else None)
    assert result['confidence'] is None


def test_multi_missing_conflicting_and_unknown(speech_route):
    def extract(text):return speech_route.post('/api/speech/parse',json={'route_id':1,'text':text}).json()['items']
    items=extract('One to BTM, two to Majestic')
    assert [i['quantity'] for i in items]==[1,2]
    assert [i['destination_stop_id'] for i in items]==[5,2]
    assert extract('to Majestic')[0]['quantity'] is None
    assert extract('two three tickets Majestic')[0]['quantity'] is None
    assert extract('21 tickets to Majestic')[0]['quantity'] is None
    assert extract('two to absent')[0]['destination_stop_id'] is None
    assert extract('two free tickets to Majestic')[0]['category'] is None
    negated=extract('not shakti two tickets to Majestic')[0]
    assert negated['category'] is None and negated['quantity'] is None and negated['destination_stop_id'] is None
    item=extract('two shakti tickets to Majestic')[0]
    assert item['category']=='shakti-demo'
    with database() as db:
        db.add_all([StopAlias(stop_id=2,alias='shared'),StopAlias(stop_id=3,alias='shared')]);db.commit()
    assert extract('two tickets to shared')[0]['destination_stop_id'] is None
    assert speech_route.get('/api/ticket-requests').json()==[]  # extraction never creates/approves


def test_fixture_label_and_live_unavailability(speech_route,monkeypatch):
    monkeypatch.setattr(settings,'speech_mode','fixture')
    data=speech_route.post('/api/speech/fixture/kn-mixed?route_id=1').json()
    assert data['is_fixture'] is True and data['provider']=='development-fixture'
    assert speech_route.get('/api/speech/status').json()['live_available'] is False
    assert speech_route.post('/api/speech/transcribe?route_id=1',content=wav_bytes(),headers={'Content-Type':'audio/wav'}).status_code==503
    monkeypatch.setattr(settings,'speech_mode','disabled')
    assert speech_route.post('/api/speech/fixture/kn-mixed?route_id=1').status_code==404


def test_documented_multipart_response(speech_route):
    def handler(request):
        assert str(request.url)=='https://api.vachana.ai/stt/v3'
        assert request.headers['X-API-Key-ID']=='test-only-key'
        body=request.read()
        for field in [b'name="audio_file"',b'filename="request.wav"',b'prisma-v3.0',b'kn-IN,en-IN',b'verbatim',b'RIFF']:
            assert field in body
        # Documented success envelope, with no fabricated confidence field.
        return httpx.Response(200,json={'success':True,'request_id':'documented-shape','transcript':'Majestic ge eradu ticket','model':'prisma-v3.0','detected_language_code':'kn-IN','processing_time':0.62,'end_to_end_latency':0.71})
    app.dependency_overrides[get_provider]=lambda:GnaniProvider('test-only-key',httpx.MockTransport(handler))
    response=speech_route.post('/api/speech/transcribe?route_id=1&language=kn-IN,en-IN',content=wav_bytes(),headers={'Content-Type':'audio/wav'})
    assert response.status_code==200,response.text
    assert response.json()['provider']=='gnani' and not response.json()['is_fixture']
    assert response.json()['items'][0]['quantity']==2


@pytest.mark.parametrize('status,payload,expected',[
    (429,{'detail':{'error_code':'RATE_LIMITED','status_code':429}},429),
    (401,{'detail':{'error_code':'INVALID_API_KEY'}},503),
    (403,{},503),(402,{},503),(500,{'success':False,'error':{'type':'INTERNAL_SERVER_ERROR'}},502),
    (400,{'success':False,'error':{'type':'AUDIO_CONVERSION_ERROR'}},422),(504,{'code':'UPSTREAM_TIMEOUT'},504),
    (200,{'success':True,'transcript':''},422),(200,{'success':True,'transcript':{'bad':'shape'}},502),
    (200,{'success':True,'transcript':'cut short','truncated':True},502),
])
def test_provider_errors(status,payload,expected):
    provider=GnaniProvider('test',httpx.MockTransport(lambda r:httpx.Response(status,json=payload)))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(provider.transcribe(wav_bytes(),'en-IN'))
    assert exc.value.status_code==expected


@pytest.mark.parametrize('failure',[httpx.ReadTimeout,httpx.ConnectError])
def test_provider_network_failure(failure):
    def handler(request):raise failure('fixture error',request=request)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(GnaniProvider('test',httpx.MockTransport(handler)).transcribe(wav_bytes(),'en-IN'))
    assert exc.value.status_code in (502,504)


@pytest.mark.parametrize('audio',[b'',b'webm-not-wav',b'RIFF',wav_bytes()[:-50],b'x'*3_000_001])
def test_invalid_audio(audio):
    with pytest.raises(HTTPException):validate_audio(audio)
