"""Gnani REST contract: https://docs.gnani.ai/api/STT/speech-to-text"""
from typing import Protocol
import io
import wave
import httpx
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, StrictBool, StrictStr, ValidationError
from app.config import settings

MAX_AUDIO_BYTES = 3_000_000


class Transcript(BaseModel):
    text: str
    provider: str
    is_fixture: bool = False
    request_id: str | None = None
    confidence: None = None  # REST docs do not provide a confidence score.


class SpeechProvider(Protocol):
    async def transcribe(self, audio: bytes, language: str) -> Transcript: ...


class GnaniResponse(BaseModel):
    model_config = ConfigDict(extra='ignore')
    success: StrictBool
    transcript: StrictStr
    request_id: StrictStr | None = None
    truncated: StrictBool = False


def validate_audio(audio):
    if not audio or len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(413, 'Audio must be nonempty and below 3 MB.')
    try:
        with wave.open(io.BytesIO(audio), 'rb') as wav:
            if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getcomptype() != 'NONE' or wav.getframerate() not in (8000, 16000, 22050, 24000, 32000, 44100, 48000):
                raise ValueError()
            frames = wav.getnframes()
            duration = frames / wav.getframerate()
            if not 0.1 <= duration <= 30 or len(wav.readframes(frames)) != frames * 2:
                raise ValueError()
    except (wave.Error, EOFError, ValueError, ZeroDivisionError):
        raise HTTPException(422, 'Use a complete mono PCM16 WAV clip between 0.1 and 30 seconds.')


class GnaniProvider:
    def __init__(self, key: str, transport=None):
        self.key, self.transport = key, transport

    async def transcribe(self, audio, language):
        validate_audio(audio)
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(45, connect=10), transport=self.transport, follow_redirects=False) as client:
                response = await client.post('https://api.vachana.ai/stt/v3',
                    headers={'X-API-Key-ID': self.key},
                    files={'audio_file': ('request.wav', audio, 'audio/wav')},
                    data={'language_code': language, 'model': 'prisma-v3.0', 'format': 'verbatim'})
        except httpx.TimeoutException:
            raise HTTPException(504, 'Speech service timed out. Retry or enter text manually.')
        except httpx.RequestError:
            raise HTTPException(502, 'Speech service unreachable. Use manual text or retry.')
        if response.status_code == 429:
            raise HTTPException(429, 'Speech rate limit reached. Wait before retrying; no automatic retry was sent.')
        if response.status_code in (401, 402, 403):
            raise HTTPException(503, 'Speech account key, permission or credit is unavailable. Contact the operator.')
        if response.status_code == 504:
            raise HTTPException(504, 'Speech service timed out. Try a shorter recording.')
        if response.status_code in (400, 413, 422):
            raise HTTPException(422, 'Gnani rejected the audio or language configuration. Retry a short WAV recording.')
        if not response.is_success:
            raise HTTPException(502, 'Speech service failed. Use manual text or retry.')
        try:
            body = GnaniResponse.model_validate(response.json())
            if not body.success or body.truncated or len(body.transcript) > 2000:
                raise ValueError()
        except (ValidationError, ValueError):
            raise HTTPException(502, 'Speech returned an invalid or incomplete response. Retry with shorter audio.')
        if not body.transcript.strip():
            raise HTTPException(422, 'No speech recognized. Retry or type the request.')
        return Transcript(text=body.transcript, provider='gnani', request_id=body.request_id)


FIXTURES = {
    'kn-mixed': 'Majestic ge eradu ticket',
    'en': 'Two tickets to Silk Board',
    'hi-mixed': 'Jayanagar ke teen ticket',
    'multi': 'One to BTM, two to Majestic',
}


def get_provider() -> SpeechProvider:
    if settings.speech_mode != 'gnani' or not settings.gnani_api_key or not settings.gnani_api_key.get_secret_value().strip():
        raise HTTPException(503, 'Live speech unavailable. Configure GNANI_API_KEY and SPEECH_MODE=gnani on the backend.')
    return GnaniProvider(settings.gnani_api_key.get_secret_value())
