from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select
from app.models import TicketRequest, Route, Stop, FareTable, FareEntry, FareRule, BatchItem, AuditEvent, SimulatedTicket
from app.schemas import TicketOut
from app.services.route_engine import resolve
from app.services.fare_engine import quote, serialize


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
    # Unknown categories cannot silently inherit a standard fare.
    if not (db.scalar(select(FareEntry.id).join(FareTable).where(FareTable.route_id == data.route_id, FareEntry.category == data.category).limit(1)) or db.scalar(select(FareRule.id).where(FareRule.route_id == data.route_id, FareRule.category == data.category).limit(1))):
        raise HTTPException(422, 'Unknown passenger category')


def journey(db, ticket):
    issues, stops = [], []
    for field in ('origin', 'destination'):
        stop_id, text = getattr(ticket, field + '_stop_id'), getattr(ticket, field + '_text')
        if text is not None:
            result = resolve(db, ticket.route_id, text)
            if result['status'] != 'resolved':
                issues.append(f'{field.title()} stop {result["status"]}. Clarification required.')
            stop_id = result['stop_id']
        stop = db.get(Stop, stop_id) if stop_id is not None else None
        if stop is None or stop.route_id != ticket.route_id:
            issues.append(f'Choose a valid {field} stop on this route.')
        stops.append(stop)
    if not issues and stops[0].position >= stops[1].position:
        issues.append('Destination must follow boarding stop in this direction.')
    return stops, issues


def evaluate(db, ticket):
    stops, issues = journey(db, ticket)
    if issues:
        return 'needs-clarification', None, issues, None
    snapshot, concession = quote(db, ticket, *stops)
    if snapshot is None:
        return 'needs-clarification', None, ['Fare unavailable'], None
    if concession:
        if not ticket.concession_verified:
            issues.append(concession.eligibility_check)
        if not ticket.documents_verified:
            issues.append(concession.document_check)
    if snapshot['total_paise'] > 0 and not ticket.payment_collected:
        issues.append('Conductor must confirm payment collection.')
    return ('pending-verification' if issues else 'ready-for-approval'), snapshot['total_paise'], issues, serialize(snapshot)


def validate(db, ticket):
    state, total, issues, snapshot = evaluate(db, ticket)
    if ticket.quote_snapshot != snapshot:
        ticket.payment_collected = ticket.concession_verified = ticket.documents_verified = False
        state, total, issues, snapshot = evaluate(db, ticket)
    ticket.state, ticket.total_paise, ticket.quote_snapshot = state, total, snapshot


def output(db, ticket):
    result = TicketOut.model_validate(ticket)
    result.batch_id = db.scalar(select(BatchItem.batch_id).where(BatchItem.ticket_request_id == ticket.id))
    if ticket.state not in ('approved', 'cancelled'):
        result.issues = evaluate(db, ticket)[2]
    return result


def audit(db, ticket, action, previous=None, actor=None):
    db.flush()
    db.add(AuditEvent(request_id=ticket.id, action=action, from_state=previous,
        to_state=ticket.state, request_version=ticket.version, actor=actor,
        snapshot=output(db, ticket).model_dump_json()))


def approve(db, ticket, name):
    current_state, total, issues, snapshot = evaluate(db, ticket)
    if current_state != 'ready-for-approval' or snapshot != ticket.quote_snapshot or total != ticket.total_paise:
        raise HTTPException(409, 'Fare or checks changed. Validate and verify again. ' + '; '.join(issues))
    ticket.state = 'approved'
    ticket.approved_by = name.strip()
    ticket.approved_at = datetime.now(timezone.utc).isoformat()
    db.add(SimulatedTicket(request_id=ticket.id, quote_snapshot=snapshot, total_paise=total, approved_by=name.strip()))
