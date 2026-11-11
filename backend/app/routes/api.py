from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Route, TicketRequest
from app.schemas import TicketCreate, TicketEdit, TicketOut, RouteOut, Version, Verification, Approval, State
from app.services import tickets as service

router = APIRouter(prefix='/api')


@router.get('/health')
def health():
    return {'status': 'ok', 'mode': 'demo', 'speech_available': False}


@router.get('/routes', response_model=list[RouteOut])
def routes(db: Session = Depends(get_db)):
    return db.scalars(select(Route).order_by(Route.id)).all()


@router.get('/ticket-requests', response_model=list[TicketOut])
def listing(state: State | None = None, limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    query = select(TicketRequest).order_by(TicketRequest.created_at.desc(), TicketRequest.id)
    if state:
        query = query.where(TicketRequest.state == state)
    return [service.output(db, t) for t in db.scalars(query.limit(limit).offset(offset))]


@router.post('/ticket-requests', response_model=TicketOut, status_code=201)
def create(data: TicketCreate, db: Session = Depends(get_db)):
    fields = data.model_dump(exclude={'client_request_id'})
    existing = db.scalar(select(TicketRequest).where(TicketRequest.client_request_id == str(data.client_request_id)))
    if existing:
        if any(getattr(existing, key) != value for key, value in fields.items()):
            raise HTTPException(409, 'Client request ID already used with different data')
        return service.output(db, existing)
    service.check_references(db, data)
    ticket = TicketRequest(**fields, client_request_id=str(data.client_request_id))
    db.add(ticket)
    db.commit()
    return service.output(db, ticket)


@router.get('/ticket-requests/{ticket_id}', response_model=TicketOut)
def detail(ticket_id: str, db: Session = Depends(get_db)):
    return service.output(db, service.get_ticket(db, ticket_id))


@router.put('/ticket-requests/{ticket_id}', response_model=TicketOut)
def edit(ticket_id: str, data: TicketEdit, db: Session = Depends(get_db)):
    ticket = service.get_ticket(db, ticket_id)
    service.guard(ticket, data.version)
    service.check_references(db, data)
    for key, value in data.model_dump(exclude={'version'}).items():
        setattr(ticket, key, value)
    ticket.state, ticket.total_paise = 'draft', None
    ticket.concession_verified = ticket.payment_collected = False
    db.commit()
    return service.output(db, ticket)


@router.post('/ticket-requests/{ticket_id}/validate', response_model=TicketOut)
def validate(ticket_id: str, data: Version, db: Session = Depends(get_db)):
    ticket = service.get_ticket(db, ticket_id)
    service.guard(ticket, data.version)
    service.validate(db, ticket)
    db.commit()
    return service.output(db, ticket)


@router.post('/ticket-requests/{ticket_id}/verify', response_model=TicketOut)
def verify(ticket_id: str, data: Verification, db: Session = Depends(get_db)):
    ticket = service.get_ticket(db, ticket_id)
    service.guard(ticket, data.version)
    if ticket.state not in ('pending-verification', 'ready-for-approval'):
        raise HTTPException(409, 'Validate the journey before verification')
    ticket.concession_verified = data.concession_verified
    ticket.payment_collected = data.payment_collected
    service.validate(db, ticket)
    db.commit()
    return service.output(db, ticket)


@router.post('/ticket-requests/{ticket_id}/approve', response_model=TicketOut)
def approve(ticket_id: str, data: Approval, db: Session = Depends(get_db)):
    ticket = service.get_ticket(db, ticket_id)
    # Safe retry after a lost approval response; never creates a second ticket.
    if ticket.state == 'approved' and ticket.version == data.version + 1 and ticket.approved_by == data.conductor_name.strip():
        return service.output(db, ticket)
    service.guard(ticket, data.version)
    if ticket.state != 'ready-for-approval':
        raise HTTPException(409, 'Request is not ready for approval')
    service.approve(db, ticket, data.conductor_name)
    db.commit()
    return service.output(db, ticket)


@router.post('/ticket-requests/{ticket_id}/cancel', response_model=TicketOut)
def cancel(ticket_id: str, data: Version, db: Session = Depends(get_db)):
    ticket = service.get_ticket(db, ticket_id)
    service.guard(ticket, data.version)
    ticket.state = 'cancelled'
    db.commit()
    return service.output(db, ticket)
