from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker
from app.database import get_db, make_engine
from app.main import app
from app.models import StopAlias, FareTable, FareEntry, TicketRequest, SimulatedTicket, AuditEvent
from app.services.migrations import migrate
from test_tickets import create, action


@contextmanager
def database():
    dependency = app.dependency_overrides[get_db]()
    db = next(dependency)
    try:
        yield db
    finally:
        dependency.close()


def ready(client, **changes):
    t, fields = create(client, **changes)
    t = action(client, t, 'validate').json()
    t = action(client, t, 'verify', payment_collected=True, concession_verified=True, documents_verified=True).json()
    assert t['state'] == 'ready-for-approval'
    return t, fields


def test_aliases_and_unknown_stop_clarification(client):
    route = client.get('/api/routes').json()[0]
    with database() as db:
        db.add_all([StopAlias(stop_id=s['id'], alias='shared') for s in route['stops'][:2]])
        db.commit()
    for text, status in [('shared', 'ambiguous'), ('absent', 'unknown'), ('  CENTRAL STOP  ', 'resolved'), ('ಕೆರೆ', 'resolved')]:
        assert client.get(f"/api/routes/{route['id']}/resolve-stop", params={'query': text}).json()['status'] == status
    for text in ['shared', 'absent']:
        t, _ = create(client, destination_stop_id=None, destination_text=text)
        t = action(client, t, 'validate').json()
        assert t['state'] == 'needs-clarification' and text not in t['issues'][0]
        assert action(client, t, 'approve', confirmed=True, conductor_name='Demo').status_code == 409
    t, _ = create(client, destination_stop_id=None, destination_text='Lake stop')
    assert action(client, t, 'validate').json()['total_paise'] == 4000


def test_missing_fare_and_service_never_fall_back(client):
    for service in ['unknown', 'express']:
        t, _ = create(client, service_type=service)
        t = action(client, t, 'validate').json()
        assert t['total_paise'] == (8000 if service == 'express' else None)
        if service == 'unknown':
            assert t['issues'] == ['Fare unavailable']
    with database() as db:
        for entry in db.scalars(select(FareEntry).where(FareEntry.category == 'standard')):
            db.delete(entry)
        db.flush()
        # keep one category configured on another stage; missing journey has no price
        db.add(FareEntry(table_id=1, service_type='ordinary', category='standard', boarding_stage=0, destination_stage=1, unit_paise=500))
        db.commit()
    t, _ = create(client)
    t = action(client, t, 'validate').json()
    assert t['issues'] == ['Fare unavailable'] and t['total_paise'] is None


def test_shakti_requires_both_manual_checks_no_payment_for_zero(client):
    t, _ = create(client, category='shakti-demo')
    t = action(client, t, 'validate').json()
    assert t['state'] == 'pending-verification' and t['total_paise'] == 0
    assert action(client, t, 'verify', payment_collected=False, concession_verified='yes').status_code == 422
    t = action(client, t, 'verify', payment_collected=False, concession_verified=True, documents_verified=False).json()
    assert t['state'] == 'pending-verification'
    t = action(client, t, 'verify', payment_collected=False, concession_verified=True, documents_verified=True).json()
    assert t['state'] == 'ready-for-approval'
    assert action(client, t, 'approve', confirmed=True, conductor_name='Demo').json()['state'] == 'approved'


def test_quantity_change_invalidates_payment(client):
    t, fields = ready(client)
    fields.pop('client_request_id')
    t = client.put(f"/api/ticket-requests/{t['id']}", json={**fields, 'passenger_count':3, 'version':t['version']}).json()
    assert t['state'] == 'draft' and not t['payment_collected']
    assert action(client, t, 'approve', confirmed=True, conductor_name='Demo').status_code == 409
    assert action(client, t, 'validate').json()['total_paise'] == 6000


def test_quote_change_blocks_and_resets_verification(client):
    t, _ = ready(client)
    with database() as db:
        table = db.get(FareTable, 1)
        table.version = 'synthetic-2'
        db.commit()
    assert action(client, t, 'approve', confirmed=True, conductor_name='Demo').status_code == 409
    assert action(client, t, 'verify', payment_collected=True, concession_verified=False).status_code == 409
    t = action(client, t, 'validate').json()
    assert not t['payment_collected'] and t['state'] == 'pending-verification'
    assert 'synthetic-2' in t['quote_snapshot']


def test_latest_table_missing_rule_no_older_fallback(client):
    with database() as db:
        db.add(FareTable(route_id=1, version='new-empty', effective_date='2026-02-01', source='Synthetic demo', is_demo=True))
        db.commit()
    t, _ = create(client)
    assert action(client, t, 'validate').json()['issues'] == ['Fare unavailable']


def test_concurrent_approval_one_record_and_one_audit(client):
    t, _ = ready(client)
    def approve(_):
        return action(client, t, 'approve', confirmed=True, conductor_name='Demo')
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(approve, range(4)))
    assert all(r.status_code == 200 for r in responses)
    record = client.get(f"/api/ticket-requests/{t['id']}/simulated-ticket").json()
    assert record['valid_for_travel'] is False and record['quote']['fare_version'] == 'synthetic-1'
    events = client.get(f"/api/ticket-requests/{t['id']}/audit").json()
    assert [e['action'] for e in events] == ['created', 'validated', 'verified', 'approved']
    with database() as db:
        assert db.scalar(select(func.count()).select_from(SimulatedTicket)) == 1
    assert action(client, t, 'approve', confirmed=True, conductor_name='Different').status_code == 409


def test_cancel_audit_and_restart_persistence(client):
    t, _ = ready(client)
    approved = action(client, t, 'approve', confirmed=True, conductor_name='Demo').json()
    c, _ = create(client)
    c = action(client, c, 'cancel').json()
    assert action(client, c, 'validate').status_code == 409
    with database() as db:
        url = str(db.bind.url)
    fresh = make_engine(url)
    migrate(fresh)  # Same initialization path after a process restart; no destructive reset.
    with sessionmaker(fresh)() as db:
        assert db.get(TicketRequest, approved['id']).state == 'approved'
        assert db.get(TicketRequest, c['id']).state == 'cancelled'
        assert db.scalar(select(SimulatedTicket)).total_paise == 4000
        assert db.scalar(select(func.count()).select_from(AuditEvent)) == 6
    fresh.dispose()


def test_expired_table_blocks_approval(client):
    t, _ = ready(client)
    with database() as db:
        db.get(FareTable, 1).expires_date = '2020-01-01'
        db.commit()
    assert action(client, t, 'approve', confirmed=True, conductor_name='Demo').status_code == 409
    t = action(client, t, 'validate').json()
    assert t['total_paise'] is None and t['issues'] == ['Fare unavailable']


def test_migration_preserves_existing_request(client):
    from sqlalchemy import text
    t, _ = create(client)
    with database() as db:
        url = str(db.bind.url)
    engine = make_engine(url)
    # Reproduce the previous ticket schema while retaining a real saved draft.
    with engine.begin() as connection:
        for column in ['service_type', 'origin_text', 'destination_text', 'documents_verified', 'quote_snapshot']:
            connection.execute(text(f'ALTER TABLE ticket_requests DROP COLUMN {column}'))
    migrate(engine)
    migrate(engine)
    with sessionmaker(engine)() as db:
        saved = db.get(TicketRequest, t['id'])
        assert saved.state == 'draft' and saved.passenger_count == 2
        assert saved.service_type == 'ordinary' and saved.quote_snapshot is None
    engine.dispose()


def test_missing_concession_policy_blocks_reduced_fare(client):
    from app.models import ConcessionRule
    with database() as db:
        for policy in db.scalars(select(ConcessionRule).where(ConcessionRule.category == 'demo-concession')):
            db.delete(policy)
        db.commit()
    t, _ = create(client, category='demo-concession')
    t = action(client, t, 'validate').json()
    assert t['issues'] == ['Fare unavailable'] and t['total_paise'] is None
