from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db, get_write_db
from app.config import settings
from app.models import Route, TicketRequest, AuditEvent, SimulatedTicket, FareTable, FareEntry, ConcessionRule
from app.schemas import TicketCreate, TicketEdit, TicketOut, RouteOut, Version, Verification, Approval, State
from app.services import tickets as service
from app.services.route_engine import resolve
import json

router = APIRouter(prefix='/api')


@router.get('/health')
def health():
    return {'status': 'ok', 'mode': 'demo', 'speech_available': settings.speech_mode == 'gnani' and bool(settings.gnani_api_key and settings.gnani_api_key.get_secret_value().strip())}


@router.get('/routes', response_model=list[RouteOut])
def routes(db: Session = Depends(get_db)):
    results = []
    for route in db.scalars(select(Route).order_by(Route.id)):
        result = RouteOut.model_validate(route)
        result.service_types = list(db.scalars(select(FareEntry.service_type).join(FareTable).where(FareTable.route_id == route.id).distinct().order_by(FareEntry.service_type)))
        results.append(result)
    return results


@router.get('/ticket-requests', response_model=list[TicketOut])
def listing(state: State | None = None, limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    query = select(TicketRequest).order_by(TicketRequest.created_at.desc(), TicketRequest.id)
    if state:
        query = query.where(TicketRequest.state == state)
    return [service.output(db, t) for t in db.scalars(query.limit(limit).offset(offset))]


@router.post('/ticket-requests', response_model=TicketOut, status_code=201)
def create(data: TicketCreate, db: Session = Depends(get_write_db)):
    fields = data.model_dump(exclude={'client_request_id'})
    existing = db.scalar(select(TicketRequest).where(TicketRequest.client_request_id == str(data.client_request_id)))
    if existing:
        if any(getattr(existing, key) != value for key, value in fields.items()):
            raise HTTPException(409, 'Client request ID already used with different data')
        return service.output(db, existing)
    service.check_references(db, data)
    ticket = TicketRequest(**fields, client_request_id=str(data.client_request_id))
    db.add(ticket)
    service.audit(db, ticket, 'created')
    db.commit()
    return service.output(db, ticket)


@router.get('/ticket-requests/{ticket_id}', response_model=TicketOut)
def detail(ticket_id: str, db: Session = Depends(get_db)):
    return service.output(db, service.get_ticket(db, ticket_id))


@router.put('/ticket-requests/{ticket_id}', response_model=TicketOut)
def edit(ticket_id: str, data: TicketEdit, db: Session = Depends(get_write_db)):
    ticket = service.get_ticket(db, ticket_id)
    service.guard(ticket, data.version)
    service.check_references(db, data)
    previous = ticket.state
    for key, value in data.model_dump(exclude={'version'}).items():
        setattr(ticket, key, value)
    ticket.state, ticket.total_paise, ticket.quote_snapshot = 'draft', None, None
    ticket.concession_verified = ticket.payment_collected = ticket.documents_verified = False
    service.audit(db, ticket, 'edited', previous)
    db.commit()
    return service.output(db, ticket)


@router.post('/ticket-requests/{ticket_id}/validate', response_model=TicketOut)
def validate(ticket_id: str, data: Version, db: Session = Depends(get_write_db)):
    ticket = service.get_ticket(db, ticket_id)
    service.guard(ticket, data.version)
    previous = ticket.state
    service.validate(db, ticket)
    service.audit(db, ticket, 'validated', previous)
    db.commit()
    return service.output(db, ticket)


@router.post('/ticket-requests/{ticket_id}/verify', response_model=TicketOut)
def verify(ticket_id: str, data: Verification, db: Session = Depends(get_write_db)):
    ticket = service.get_ticket(db, ticket_id)
    service.guard(ticket, data.version)
    if ticket.state not in ('pending-verification', 'ready-for-approval'):
        raise HTTPException(409, 'Validate the journey before verification')
    previous = ticket.state
    # A changed table must be revalidated before accepting confirmations.
    if service.evaluate(db, ticket)[3] != ticket.quote_snapshot:
        raise HTTPException(409, 'Fare changed. Validate before verification.')
    ticket.documents_verified = data.documents_verified
    ticket.concession_verified = data.concession_verified
    ticket.payment_collected = data.payment_collected
    service.validate(db, ticket)
    service.audit(db, ticket, 'verified', previous)
    db.commit()
    return service.output(db, ticket)


@router.post('/ticket-requests/{ticket_id}/approve', response_model=TicketOut)
def approve(ticket_id: str, data: Approval, db: Session = Depends(get_write_db)):
    ticket = service.get_ticket(db, ticket_id)
    # Safe retry after a lost approval response; never creates a second ticket.
    if ticket.state == 'approved' and ticket.version in (data.version, data.version + 1) and ticket.approved_by == data.conductor_name.strip():
        return service.output(db, ticket)
    service.guard(ticket, data.version)
    if ticket.state != 'ready-for-approval':
        raise HTTPException(409, 'Request is not ready for approval')
    previous = ticket.state
    service.approve(db, ticket, data.conductor_name)
    service.audit(db, ticket, 'approved', previous, data.conductor_name.strip())
    db.commit()
    return service.output(db, ticket)


@router.post('/ticket-requests/{ticket_id}/cancel', response_model=TicketOut)
def cancel(ticket_id: str, data: Version, db: Session = Depends(get_write_db)):
    ticket = service.get_ticket(db, ticket_id)
    service.guard(ticket, data.version)
    previous = ticket.state
    ticket.state = 'cancelled'
    service.audit(db, ticket, 'cancelled', previous)
    db.commit()
    return service.output(db, ticket)


@router.get('/routes/{route_id}/resolve-stop')
def resolve_stop(route_id: int, query: str = Query(min_length=1, max_length=100), db: Session = Depends(get_db)):
    if not db.get(Route, route_id):
        raise HTTPException(404, 'Unknown route')
    return resolve(db, route_id, query)


@router.get('/routes/{route_id}/fare-tables')
def fare_tables(route_id: int, db: Session = Depends(get_db)):
    tables = db.scalars(select(FareTable).where(FareTable.route_id == route_id)).all()
    return [{'id': t.id, 'version': t.version, 'source': t.source, 'is_demo': t.is_demo,
        'effective_date': t.effective_date, 'expires_date': t.expires_date,
        'entries': [{k: getattr(e, k) for k in ('service_type', 'category', 'boarding_stage', 'destination_stage', 'unit_paise', 'concession_required')} for e in t.entries],
        'concessions': [{k: getattr(c, k) for k in ('category', 'service_type', 'label', 'eligibility_check', 'document_check', 'is_demo')} for c in db.scalars(select(ConcessionRule).where(ConcessionRule.table_id == t.id))]} for t in tables]


@router.get('/ticket-requests/{ticket_id}/audit')
def audit_events(ticket_id: str, db: Session = Depends(get_db)):
    service.get_ticket(db, ticket_id)
    return [{'id': e.id, 'action': e.action, 'from_state': e.from_state, 'to_state': e.to_state,
        'version': e.request_version, 'actor': e.actor, 'created_at': e.created_at,
        'snapshot': json.loads(e.snapshot)} for e in db.scalars(select(AuditEvent).where(AuditEvent.request_id == ticket_id).order_by(AuditEvent.id))]


@router.get('/ticket-requests/{ticket_id}/simulated-ticket')
def simulated_ticket(ticket_id: str, db: Session = Depends(get_db)):
    record = db.scalar(select(SimulatedTicket).where(SimulatedTicket.request_id == ticket_id))
    if record is None:
        raise HTTPException(404, 'No simulated ticket')
    return {'id': record.id, 'request_id': record.request_id, 'total_paise': record.total_paise,
        'approved_by': record.approved_by, 'created_at': record.created_at,
        'quote': json.loads(record.quote_snapshot), 'valid_for_travel': False}
