from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

State = Literal['draft', 'needs-clarification', 'pending-verification', 'ready-for-approval', 'approved', 'cancelled']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class TicketFields(StrictModel):
    route_id: int = Field(gt=0)
    origin_stop_id: int | None = Field(default=None, gt=0)
    destination_stop_id: int | None = Field(default=None, gt=0)
    passenger_count: int = Field(default=1, ge=1, le=20)
    category: str = Field(default='standard', min_length=1, max_length=60)
    language: Literal['en-IN', 'kn-IN', 'hi-IN'] = 'en-IN'
    service_type: str = Field(default='ordinary', min_length=1, max_length=60)
    origin_text: str | None = Field(default=None, max_length=100)
    destination_text: str | None = Field(default=None, max_length=100)

    @model_validator(mode='after')
    def stop_inputs(self):
        if (self.origin_stop_id is not None and self.origin_text is not None) or (self.destination_stop_id is not None and self.destination_text is not None):
            raise ValueError('Supply a stop ID or text, not both')
        return self


class TicketCreate(TicketFields):
    client_request_id: UUID


class TicketEdit(TicketFields):
    version: int = Field(ge=1)


class Version(StrictModel):
    version: int = Field(ge=1)


class Verification(Version):
    concession_verified: StrictBool
    payment_collected: StrictBool
    documents_verified: StrictBool = False


class Approval(Version):
    confirmed: StrictBool

    @model_validator(mode='after')
    def explicit_confirmation(self):
        if self.confirmed is not True:
            raise ValueError('Explicit confirmation required')
        return self
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
    concession_verified: StrictBool
    payment_collected: StrictBool
    documents_verified: StrictBool = False
    total_paise: int | None
    approved_by: str | None
    approved_at: str | None
    created_at: str
    version: int
    service_type: str
    origin_text: str | None
    destination_text: str | None
    documents_verified: bool
    quote_snapshot: str | None
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
    service_types: list[str] = []
