from typing import Literal
from uuid import UUID
from pydantic import Field, StrictInt
from app.schemas import StrictModel, Version


class BatchDraft(StrictModel):
    origin_stop_id: int | None = Field(default=None, gt=0)
    destination_stop_id: int | None = Field(default=None, gt=0)
    destination_text: str = Field(default='', max_length=200)
    quantity: StrictInt | None = Field(default=None, ge=1, le=20)
    category: str | None = Field(default=None, max_length=60)
    service_type: str = Field(default='ordinary', min_length=1, max_length=60)
    language: Literal['kn-IN','hi-IN','en-IN'] = 'en-IN'


class BatchCreate(StrictModel):
    client_batch_id: UUID
    route_id: int = Field(gt=0)
    original_transcription: str = Field(min_length=1, max_length=2000)
    source: Literal['gnani','manual-text','development-fixture'] = 'manual-text'
    items: list[BatchDraft] | None = Field(default=None, min_length=1, max_length=30)


class BatchEdit(Version):
    draft: BatchDraft


class BatchPrepare(StrictModel):
    versions: dict[str, int] = Field(max_length=30)
