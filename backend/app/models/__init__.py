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
    __mapper_args__ = {'version_id_col': version}
