import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, or_
from app.models import FareTable, FareEntry, ConcessionRule


def quote(db, ticket, origin, destination):
    today = datetime.now(timezone(timedelta(hours=5, minutes=30))).date().isoformat()
    tables = db.scalars(select(FareTable).where(FareTable.route_id == ticket.route_id,
        FareTable.effective_date <= today, or_(FareTable.expires_date.is_(None), FareTable.expires_date >= today))
        .order_by(FareTable.effective_date.desc())).all()
    # Never fall back to an older table or guess a service/category price.
    if not tables or (len(tables) > 1 and tables[0].effective_date == tables[1].effective_date):
        return None, None
    table = tables[0]
    entry = db.scalar(select(FareEntry).where(FareEntry.table_id == table.id,
        FareEntry.service_type == ticket.service_type, FareEntry.category == ticket.category,
        FareEntry.boarding_stage == origin.position, FareEntry.destination_stage == destination.position))
    concession = db.scalar(select(ConcessionRule).where(ConcessionRule.table_id == table.id,
        ConcessionRule.category == ticket.category, ConcessionRule.service_type == ticket.service_type))
    if entry is None or entry.unit_paise < 0 or ((entry.concession_required or entry.unit_paise == 0) and concession is None):
        return None, None
    snapshot = {'table_id': table.id, 'fare_version': table.version, 'source': table.source,
        'effective_date': table.effective_date, 'expires_date': table.expires_date, 'is_demo': table.is_demo,
        'entry_id': entry.id, 'concession_required': entry.concession_required, 'route_id': ticket.route_id, 'service_type': ticket.service_type,
        'boarding_stage': origin.position, 'destination_stage': destination.position,
        'category': ticket.category, 'quantity': ticket.passenger_count, 'unit_paise': entry.unit_paise,
        'total_paise': entry.unit_paise * ticket.passenger_count,
        'concession': None if concession is None else {'id': concession.id, 'label': concession.label,
            'eligibility_check': concession.eligibility_check, 'document_check': concession.document_check, 'is_demo': concession.is_demo}}
    return snapshot, concession


def serialize(snapshot):
    return json.dumps(snapshot, sort_keys=True, ensure_ascii=False)
