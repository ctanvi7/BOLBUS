from uuid import uuid4
import pytest
from app.models import Route, Stop
from app.database import get_db
from app.main import app


def create(client, **changes):
    route = client.get('/api/routes').json()[0]
    data = dict(client_request_id=str(uuid4()), route_id=route['id'], origin_stop_id=route['stops'][0]['id'], destination_stop_id=route['stops'][-1]['id'], passenger_count=2)
    data.update(changes)
    response = client.post('/api/ticket-requests', json=data)
    assert response.status_code == 201, response.text
    return response.json(), data


def action(client, ticket, name, **extra):
    return client.post(f"/api/ticket-requests/{ticket['id']}/{name}", json={'version':ticket['version'], **extra})


def test_explicit_approval_and_persistence(client):
    t, _ = create(client)
    assert t['state'] == 'draft' and t['total_paise'] is None
    assert action(client,t,'approve',confirmed=True,conductor_name='Tanvi').status_code == 409
    t = action(client,t,'validate').json()
    assert t['state'] == 'pending-verification' and t['total_paise'] == 4000
    t = action(client,t,'verify',payment_collected=True,concession_verified=False).json()
    assert t['state'] == 'ready-for-approval'
    assert action(client,t,'approve',confirmed=False,conductor_name='Tanvi').status_code == 422
    response = action(client,t,'approve',confirmed=True,conductor_name='Tanvi')
    assert response.status_code == 200
    approved = response.json()
    assert approved['state'] == 'approved' and approved['approved_at']
    assert action(client,t,'approve',confirmed=True,conductor_name='Tanvi').json()['id'] == approved['id']
    assert client.get(f"/api/ticket-requests/{t['id']}").json()['approved_by'] == 'Tanvi'
    assert client.get('/api/ticket-requests?state=approved').json()[0]['id'] == t['id']
    assert action(client,approved,'cancel').status_code == 409


def test_concession_requires_manual_check(client):
    t, _ = create(client, category='demo-concession')
    t = action(client,t,'validate').json()
    assert t['total_paise'] == 2000
    t = action(client,t,'verify',payment_collected=True,concession_verified=False).json()
    assert t['state'] == 'pending-verification'
    t = action(client,t,'verify',payment_collected=True,concession_verified=True).json()
    assert t['state'] == 'ready-for-approval'


@pytest.mark.parametrize('change', [{'destination_stop_id':None},{'origin_stop_id':None}])
def test_incomplete_journey_needs_clarification(client,change):
    t, _ = create(client,**change)
    t = action(client,t,'validate').json()
    assert t['state'] == 'needs-clarification' and t['total_paise'] is None
    assert action(client,t,'verify',payment_collected=True,concession_verified=True).status_code == 409


def test_reverse_and_same_stop(client):
    route = client.get('/api/routes').json()[0]
    for origin in [route['stops'][-1]['id'],route['stops'][0]['id']]:
        t, _ = create(client,origin_stop_id=origin,destination_stop_id=route['stops'][0]['id'])
        assert action(client,t,'validate').json()['state'] == 'needs-clarification'


def test_edit_resets_checks_and_stale_revision_rejected(client):
    t, fields = create(client)
    t = action(client,t,'validate').json()
    t = action(client,t,'verify',payment_collected=True,concession_verified=True).json()
    fields.pop('client_request_id')
    response = client.put(f"/api/ticket-requests/{t['id']}",json={**fields,'passenger_count':3,'version':t['version']})
    edited = response.json()
    assert edited['state']=='draft' and edited['total_paise'] is None
    assert not edited['payment_collected'] and not edited['concession_verified']
    assert action(client,t,'cancel').status_code==409


def test_creation_retry_and_cancel(client):
    t,data = create(client)
    assert client.post('/api/ticket-requests',json=data).json()['id']==t['id']
    assert len(client.get('/api/ticket-requests').json())==1
    assert client.post('/api/ticket-requests',json={**data,'passenger_count':3}).status_code==409
    t = action(client,t,'cancel').json()
    assert t['state']=='cancelled'
    assert action(client,t,'validate').status_code==409


@pytest.mark.parametrize('change', [{'passenger_count':0},{'passenger_count':21},{'route_id':999},{'origin_stop_id':999},{'category':'official-free'},{'language':'xx'},{'state':'approved'}])
def test_invalid_data_rejected(client,change):
    route=client.get('/api/routes').json()[0]
    data={'client_request_id':str(uuid4()),'route_id':route['id'],**change}
    assert client.post('/api/ticket-requests',json=data).status_code==422


def test_foreign_route_stop_rejected(client):
    # Use a separate session context to keep the DB available throughout setup.
    with next(app.dependency_overrides[get_db]()) as db:
        route=Route(code='OTHER',name='Other demo')
        db.add(route); db.flush()
        stop=Stop(route_id=route.id,position=0,name='Other',name_kn='Other',name_hi='Other')
        db.add(stop); db.commit(); stop_id=stop.id
    original=client.get('/api/routes').json()[0]
    assert client.post('/api/ticket-requests',json={'client_request_id':str(uuid4()),'route_id':original['id'],'origin_stop_id':stop_id}).status_code==422


def test_demo_disclosure_and_missing_resource(client):
    route=client.get('/api/routes').json()[0]
    assert route['is_demo'] and 'not an official BMTC' in route['fare_rules'][0]['source']
    assert client.get('/api/ticket-requests/missing').status_code==404
    assert client.get('/api/ticket-requests?state=unknown').status_code==422
