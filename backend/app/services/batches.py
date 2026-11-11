import json
from time import perf_counter
from uuid import uuid5, NAMESPACE_URL
from fastapi import HTTPException
from sqlalchemy import select
from app.models import TicketBatch, BatchItem, TicketRequest, Stop, Route
from app.schemas import TicketFields
from app.schemas.batches import BatchDraft
from app.services.speech.parser import parse
from app.services import tickets
from app.services.route_engine import resolve, suggestions


def get_batch(db, batch_id):
    batch = db.get(TicketBatch, batch_id)
    if batch is None:
        raise HTTPException(404, 'Batch not found')
    return batch


def get_item(db, batch_id, item_id):
    get_batch(db, batch_id)
    item = db.get(BatchItem, item_id)
    if item is None or item.batch_id != batch_id:
        raise HTTPException(404, 'Batch item not found')
    return item


def guard(item, version):
    if item.version != version:
        raise HTTPException(409, 'Batch item changed. Reload and compare your retained edits.')
    if item.cancelled or item.ticket_request_id:
        raise HTTPException(409, 'Prepared or cancelled items cannot be edited here. Resume the linked ticket.')


def issues_for(db, batch, draft):
    issues = []
    destination = db.get(Stop, draft.destination_stop_id) if draft.destination_stop_id else None
    # A proposal is never a resolution. Unknown/ambiguous text still requires a selected ID.
    if destination is None or destination.route_id != batch.route_id:
        issues.append('Select a valid route destination explicitly.')
    if draft.origin_stop_id is None:
        issues.append('Choose boarding stage.')
    if draft.quantity is None:
        issues.append('Confirm quantity.')
    if not draft.category:
        issues.append('Confirm category.')
    return issues


def output(db, batch):
    rows = []
    for item in batch.items:
        draft = BatchDraft.model_validate_json(item.draft_json)
        ticket = db.get(TicketRequest, item.ticket_request_id) if item.ticket_request_id else None
        issues = issues_for(db, batch, draft) if ticket is None and not item.cancelled else []
        rows.append({'id': item.id, 'position': item.position, 'version': item.version,
            'draft': draft.model_dump(), 'ticket': tickets.output(db, ticket).model_dump() if ticket else None,
            'state': ticket.state if ticket else 'cancelled' if item.cancelled else 'needs-clarification' if issues or item.last_error else 'draft',
            'issues': issues, 'last_error': item.last_error,
            'alternatives': suggestions(db, batch.route_id, draft.destination_text) if draft.destination_stop_id is None else []})
    return {'id': batch.id, 'route_id': batch.route_id, 'original_transcription': batch.original_transcription,
        'source': batch.source, 'created_at': batch.created_at, 'items': rows}


def create(db, data):
    if db.get(Route, data.route_id) is None:
        raise HTTPException(422, 'Unknown route')
    payload = data.model_dump_json()
    existing = db.scalar(select(TicketBatch).where(TicketBatch.client_batch_id == str(data.client_batch_id)))
    if existing:
        if existing.creation_payload != payload:
            raise HTTPException(409, 'Batch creation key already used with different input')
        return existing
    extraction = parse(db, data.route_id, data.original_transcription)
    if not extraction.items or len(extraction.items) > 30:
        raise HTTPException(422, 'Use between 1 and 30 separate requests per batch.')
    if data.items is not None and len(data.items) != len(extraction.items):
        raise HTTPException(422, 'Keep one batch item per extracted clause.')
    batch = TicketBatch(client_batch_id=str(data.client_batch_id), route_id=data.route_id,
        original_transcription=data.original_transcription, source=data.source, creation_payload=payload)
    db.add(batch); db.flush()
    for position, extracted in enumerate(extraction.items):
        draft = data.items[position] if data.items else BatchDraft(destination_stop_id=extracted.destination_stop_id,
            destination_text=extracted.destination, quantity=extracted.quantity, category=extracted.category)
        db.add(BatchItem(batch_id=batch.id, position=position, draft_json=draft.model_dump_json()))
    db.flush()
    db.expire(batch, ['items'])
    return batch


def prepare_item(db, batch, item, version):
    # Stable link provides recovery even after ticket details/state have changed.
    if item.ticket_request_id:
        return db.get(TicketRequest, item.ticket_request_id)
    guard(item, version)
    draft = BatchDraft.model_validate_json(item.draft_json)
    issues = issues_for(db, batch, draft)
    if issues:
        raise HTTPException(422, ' '.join(issues))
    fields = TicketFields(route_id=batch.route_id, origin_stop_id=draft.origin_stop_id,
        destination_stop_id=draft.destination_stop_id, passenger_count=draft.quantity,
        category=draft.category, service_type=draft.service_type, language=draft.language)
    tickets.check_references(db, fields)
    ticket = TicketRequest(**fields.model_dump(), client_request_id=str(uuid5(NAMESPACE_URL, 'bolbus:batch-item:' + item.id)))
    db.add(ticket)
    tickets.audit(db, ticket, 'created-from-batch')
    previous = ticket.state
    tickets.validate(db, ticket)
    tickets.audit(db, ticket, 'validated', previous)
    item.ticket_request_id = ticket.id
    item.last_error = None
    db.flush()
    return ticket


def prepare(db, batch, versions):
    start = perf_counter()
    results = []
    for item in batch.items:
        if item.id not in versions:
            continue
        try:
            with db.begin_nested():
                ticket = prepare_item(db, batch, item, versions[item.id])
            results.append({'item_id': item.id, 'ok': True, 'ticket_id': ticket.id})
        except HTTPException as exc:
            # Only persist a failure against the same unprepared revision.
            if not item.ticket_request_id and item.version == versions[item.id] and not item.cancelled:
                item.last_error = str(exc.detail)
            results.append({'item_id': item.id, 'ok': False, 'status': exc.status_code, 'error': exc.detail})
    unknown = set(versions) - {i.id for i in batch.items}
    results.extend({'item_id': item_id, 'ok': False, 'status': 404, 'error': 'Item not in this batch'} for item_id in unknown)
    db.flush()
    return {'results': results, 'processing_ms': round((perf_counter()-start)*1000, 3), 'batch': output(db, batch)}
