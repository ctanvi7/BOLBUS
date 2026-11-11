from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import Route
from app.services.speech.provider import FIXTURES, MAX_AUDIO_BYTES, get_provider
from app.services.speech.parser import parse

router = APIRouter(prefix='/api/speech', tags=['speech'])


class TextInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    route_id: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=2000)


def check_route(db, route_id):
    if not db.get(Route, route_id):
        raise HTTPException(404, 'Select a valid route first.')


@router.get('/status')
def status():
    available = settings.speech_mode == 'gnani' and bool(settings.gnani_api_key and settings.gnani_api_key.get_secret_value().strip())
    return {'mode': settings.speech_mode, 'live_available': available,
        'fixtures': list(FIXTURES) if settings.speech_mode == 'fixture' else [], 'max_seconds': 30}


@router.post('/parse')
def parse_text(data: TextInput, db: Session = Depends(get_db)):
    check_route(db, data.route_id)
    return {'route_id': data.route_id, 'provider': 'manual-text', 'is_fixture': False, **parse(db, data.route_id, data.text).model_dump()}


@router.post('/fixture/{name}')
def fixture(name: str, route_id: int, db: Session = Depends(get_db)):
    if settings.speech_mode != 'fixture' or name not in FIXTURES:
        raise HTTPException(404, 'Development fixture unavailable.')
    check_route(db, route_id)
    return {'route_id': route_id, 'provider': 'development-fixture', 'is_fixture': True, **parse(db, route_id, FIXTURES[name]).model_dump()}


@router.post('/transcribe')
async def transcribe(request: Request, route_id: int,
    language: Literal['kn-IN','hi-IN','en-IN','kn-IN,en-IN','hi-IN,en-IN'] = 'kn-IN,en-IN',
    db: Session = Depends(get_db), provider=Depends(get_provider)):
    check_route(db, route_id)
    if request.headers.get('content-type','').split(';')[0] != 'audio/wav':
        raise HTTPException(415, 'Upload audio/wav; compressed browser WebM is not accepted.')
    audio = bytearray()
    async for chunk in request.stream():
        audio.extend(chunk)
        if len(audio) > MAX_AUDIO_BYTES:
            raise HTTPException(413, 'Audio exceeds 3 MB.')
    result = await provider.transcribe(bytes(audio), language)
    return {'route_id': route_id, **result.model_dump(), **parse(db, route_id, result.text).model_dump()}
