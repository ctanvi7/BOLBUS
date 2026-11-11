from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Route(Base):
    __tablename__ = 'routes'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    is_demo: Mapped[bool] = mapped_column(default=True)
    stops: Mapped[list['Stop']] = relationship(order_by='Stop.position')
    fare_rules: Mapped[list['FareRule']] = relationship()


class Stop(Base):
    __tablename__ = 'stops'
    __table_args__ = (UniqueConstraint('route_id', 'position'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey('routes.id'))
    position: Mapped[int]
    name: Mapped[str]
    name_kn: Mapped[str]
    name_hi: Mapped[str]


class FareRule(Base):
    __tablename__ = 'fare_rules'
    __table_args__ = (UniqueConstraint('route_id', 'category'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey('routes.id'))
    category: Mapped[str]
    label: Mapped[str]
    per_stage_paise: Mapped[int]
    verification_required: Mapped[bool]
    source: Mapped[str] = mapped_column(default='Invented demonstration rule; not an official BMTC fare or concession')


class TicketRequest(Base):
    __tablename__ = 'ticket_requests'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    client_request_id: Mapped[str] = mapped_column(unique=True)
    route_id: Mapped[int] = mapped_column(ForeignKey('routes.id'))
    origin_stop_id: Mapped[int | None] = mapped_column(ForeignKey('stops.id'))
    destination_stop_id: Mapped[int | None] = mapped_column(ForeignKey('stops.id'))
    passenger_count: Mapped[int] = mapped_column(default=1)
    category: Mapped[str] = mapped_column(default='standard')
    language: Mapped[str] = mapped_column(default='en-IN')
    state: Mapped[str] = mapped_column(default='draft')
    concession_verified: Mapped[bool] = mapped_column(default=False)
    payment_collected: Mapped[bool] = mapped_column(default=False)
    total_paise: Mapped[int | None]
    approved_by: Mapped[str | None]
    approved_at: Mapped[str | None]
    created_at: Mapped[str] = mapped_column(default=lambda: datetime.now(timezone.utc).isoformat())
    version: Mapped[int] = mapped_column(default=1)
    service_type: Mapped[str] = mapped_column(default='ordinary')
    origin_text: Mapped[str | None]
    destination_text: Mapped[str | None]
    documents_verified: Mapped[bool] = mapped_column(default=False)
    quote_snapshot: Mapped[str | None]
    __mapper_args__ = {'version_id_col': version}


class StopAlias(Base):
    __tablename__ = 'stop_aliases'
    __table_args__ = (UniqueConstraint('stop_id', 'alias'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    stop_id: Mapped[int] = mapped_column(ForeignKey('stops.id'))
    alias: Mapped[str]


class FareTable(Base):
    __tablename__ = 'fare_tables'
    __table_args__ = (UniqueConstraint('route_id', 'version'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey('routes.id'))
    version: Mapped[str]
    source: Mapped[str]
    effective_date: Mapped[str]
    expires_date: Mapped[str | None]
    is_demo: Mapped[bool] = mapped_column(default=True)
    entries: Mapped[list['FareEntry']] = relationship()


class FareEntry(Base):
    __tablename__ = 'fare_entries'
    __table_args__ = (UniqueConstraint('table_id', 'service_type', 'category', 'boarding_stage', 'destination_stage'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    table_id: Mapped[int] = mapped_column(ForeignKey('fare_tables.id'))
    service_type: Mapped[str]
    category: Mapped[str]
    boarding_stage: Mapped[int]
    destination_stage: Mapped[int]
    unit_paise: Mapped[int]
    concession_required: Mapped[bool] = mapped_column(default=False)


class ConcessionRule(Base):
    __tablename__ = 'concession_rules'
    __table_args__ = (UniqueConstraint('table_id', 'category', 'service_type'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    table_id: Mapped[int] = mapped_column(ForeignKey('fare_tables.id'))
    category: Mapped[str]
    service_type: Mapped[str]
    label: Mapped[str]
    eligibility_check: Mapped[str]
    document_check: Mapped[str]
    is_demo: Mapped[bool] = mapped_column(default=True)


class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey('ticket_requests.id'))
    action: Mapped[str]
    from_state: Mapped[str | None]
    to_state: Mapped[str]
    request_version: Mapped[int]
    actor: Mapped[str | None]
    snapshot: Mapped[str]
    created_at: Mapped[str] = mapped_column(default=lambda: datetime.now(timezone.utc).isoformat())


class SimulatedTicket(Base):
    __tablename__ = 'simulated_tickets'
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    request_id: Mapped[str] = mapped_column(ForeignKey('ticket_requests.id'), unique=True)
    quote_snapshot: Mapped[str]
    total_paise: Mapped[int]
    approved_by: Mapped[str]
    created_at: Mapped[str] = mapped_column(default=lambda: datetime.now(timezone.utc).isoformat())


class TicketBatch(Base):
    __tablename__ = 'ticket_batches'
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    client_batch_id: Mapped[str] = mapped_column(unique=True)
    route_id: Mapped[int] = mapped_column(ForeignKey('routes.id'))
    original_transcription: Mapped[str]
    source: Mapped[str]
    creation_payload: Mapped[str]
    created_at: Mapped[str] = mapped_column(default=lambda: datetime.now(timezone.utc).isoformat())
    items: Mapped[list['BatchItem']] = relationship(order_by='BatchItem.position')


class BatchItem(Base):
    __tablename__ = 'batch_items'
    __table_args__ = (UniqueConstraint('batch_id', 'position'),)
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    batch_id: Mapped[str] = mapped_column(ForeignKey('ticket_batches.id'))
    position: Mapped[int]
    draft_json: Mapped[str]
    ticket_request_id: Mapped[str | None] = mapped_column(ForeignKey('ticket_requests.id'), unique=True)
    cancelled: Mapped[bool] = mapped_column(default=False)
    last_error: Mapped[str | None]
    version: Mapped[int] = mapped_column(default=1)
    __mapper_args__ = {'version_id_col': version}
