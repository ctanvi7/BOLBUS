from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select
from app.models import TicketRequest, Route, Stop, FareRule
from app.schemas import TicketOut


def get_ticket(db, ticket_id):
    ticket = db.get(TicketRequest, ticket_id)
    if not ticket:
        raise HTTPException(404, 'Ticket request not found')
    return ticket


def guard(ticket, version):
    if ticket.version != version:
        raise HTTPException(409, 'Request changed. Refresh before trying again.')
    if ticket.state in ('approved', 'cancelled'):
        raise HTTPException(409, 'Approved and cancelled requests are immutable')


def check_references(db, data):
    if not db.get(Route, data.route_id):
        raise HTTPException(422, 'Unknown route')
    for stop_id in (data.origin_stop_id, data.destination_stop_id):
        if stop_id is not None:
            stop = db.get(Stop, stop_id)
            if not stop or stop.route_id != data.route_id:
                raise HTTPException(422, 'Stop does not belong to selected route')
    if not db.scalar(select(FareRule).where(FareRule.route_id == data.route_id, FareRule.category == data.category)):
        raise HTTPException(422, 'No fare rule for category')


def evaluate(db, ticket):
    issues = []
    if ticket.origin_stop_id is None or ticket.destination_stop_id is None:
        issues.append('Choose both boarding and destination stops.')
    else:
        origin, destination = db.get(Stop, ticket.origin_stop_id), db.get(Stop, ticket.destination_stop_id)
        if origin.position >= destination.position:
            issues.append('Destination must follow boarding stop in this direction.')
    if issues:
        return 'needs-clarification', None, issues
    rule = db.scalar(select(FareRule).where(FareRule.route_id == ticket.route_id, FareRule.category == ticket.category))
    total = (destination.position - origin.position) * rule.per_stage_paise * ticket.passenger_count
    if rule.verification_required and not ticket.concession_verified:
        issues.append('Conductor must check the demo concession eligibility.')
    if not ticket.payment_collected:
        issues.append('Conductor must confirm payment collection.')
    return ('pending-verification' if issues else 'ready-for-approval'), total, issues


def validate(db, ticket):
    ticket.state, ticket.total_paise, _ = evaluate(db, ticket)


def output(db, ticket):
    result = TicketOut.model_validate(ticket)
    if ticket.state not in ('approved', 'cancelled'):
        result.issues = evaluate(db, ticket)[2]
    return result


def approve(db, ticket, name):
    validate(db, ticket)
    if ticket.state != 'ready-for-approval':
        raise HTTPException(409, 'Validation and conductor verification must be complete')
    ticket.state = 'approved'
    ticket.approved_by = name.strip()
    ticket.approved_at = datetime.now(timezone.utc).isoformat()
