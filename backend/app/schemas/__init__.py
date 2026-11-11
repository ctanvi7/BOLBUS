from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

State = Literal['draft', 'needs-clarification', 'pending-verification', 'ready-for-approval', 'approved', 'cancelled']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class TicketFields(StrictModel):
    route_id: int = Field(gt=0)
    origin_stop_id: int | None = Field(default=None, gt=0)
    destination_stop_id: int | None = Field(default=None, gt=0)
    passenger_count: int = Field(default=1, ge=1, le=20)
    category: Literal['standard', 'demo-concession'] = 'standard'
    language: Literal['en-IN', 'kn-IN', 'hi-IN'] = 'en-IN'


class TicketCreate(TicketFields):
    client_request_id: UUID


class TicketEdit(TicketFields):
    version: int = Field(ge=1)


class Version(StrictModel):
    version: int = Field(ge=1)


class Verification(Version):
    concession_verified: bool
    payment_collected: bool


class Approval(Version):
    confirmed: Literal[True]
    conductor_name: str = Field(min_length=1, max_length=80, pattern=r'.*\S.*')


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    client_request_id: str
    route_id: int
    origin_stop_id: int | None
    destination_stop_id: int | None
    passenger_count: int
    category: str
    language: str
    state: State
    concession_verified: bool
    payment_collected: bool
    total_paise: int | None
    approved_by: str | None
    approved_at: str | None
    created_at: str
    version: int
    issues: list[str] = []


class StopOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    position: int
    name: str
    name_kn: str
    name_hi: str


class FareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    category: str
    label: str
    per_stage_paise: int
    verification_required: bool
    source: str


class RouteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    is_demo: bool
    stops: list[StopOut]
    fare_rules: list[FareOut]
