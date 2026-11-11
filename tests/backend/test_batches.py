import time
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker
from app.models import Stop, FareEntry, TicketBatch, BatchItem, SimulatedTicket
from app.database import make_engine
from test_engine import database
from test_tickets import action


def create_batch(client, text='Two Market, one College, three Lake'):
    response=client.post('/api/batches',json={'client_batch_id':str(uuid4()),'route_id':1,'original_transcription':text})
    assert response.status_code==201,response.text
    return response.json()


def complete(client,batch,item,category='standard'):
    return client.put(f"/api/batches/{batch['id']}/items/{item['id']}",json={'version':item['version'],'draft':{**item['draft'],'origin_stop_id':1,'category':category}}).json()


def prepare(client,batch):
    return client.post(f"/api/batches/{batch['id']}/prepare",json={'versions':{i['id']:i['version'] for i in batch['items']}}).json()


def test_multi_destination_and_recovery(client):
    batch=create_batch(client)
    assert len(batch['items'])==3
    assert [i['draft']['quantity'] for i in batch['items']]==[2,1,3]
    for item in batch['items']:
        batch=complete(client,batch,item)
    saved=client.get(f"/api/batches/{batch['id']}").json()
    assert saved==batch
    result=prepare(client,batch)
    assert all(r['ok'] for r in result['results'])
    assert result['processing_ms']>=0
    items=result['batch']['items']
    assert len({i['ticket']['id'] for i in items})==3
    assert [i['ticket']['total_paise'] for i in items]==[1000,1000,6000]
    assert all(i['state']=='pending-verification' for i in items)
    assert result['batch']['original_transcription']=='Two Market, one College, three Lake'
    assert [i['ticket']['id'] for i in prepare(client,result['batch'])['batch']['items']]==[i['ticket']['id'] for i in items]


def test_code_mixed_unknown_and_explicit_alternative(client):
    batch=create_batch(client,'Market ge eradu ticket, Lake ke teen ticket, one Markit')
    assert [i['draft']['quantity'] for i in batch['items']]==[2,3,1]
    unknown=batch['items'][2]
    assert unknown['draft']['destination_stop_id'] is None
    assert unknown['alternatives'][0]['name']=='Market'
    result=prepare(client,batch)
    assert not result['results'][2]['ok'] and result['batch']['items'][2]['ticket'] is None
    item=result['batch']['items'][2]
    updated=client.put(f"/api/batches/{batch['id']}/items/{item['id']}",json={'version':item['version'],'draft':{**item['draft'],'origin_stop_id':1,'destination_stop_id':2,'category':'standard'}}).json()
    final=prepare(client,updated)
    assert final['batch']['items'][2]['ticket']['destination_stop_id']==2


def test_creation_retry_stale_edit_and_cancel(client):
    data={'client_batch_id':str(uuid4()),'route_id':1,'original_transcription':'two Market'}
    batch=client.post('/api/batches',json=data).json()
    assert client.post('/api/batches',json=data).json()['id']==batch['id']
    assert client.post('/api/batches',json={**data,'original_transcription':'three Market'}).status_code==409
    item=batch['items'][0];updated=complete(client,batch,item)
    assert client.put(f"/api/batches/{batch['id']}/items/{item['id']}",json={'version':item['version'],'draft':item['draft']}).status_code==409
    current=updated['items'][0]
    cancelled=client.post(f"/api/batches/{batch['id']}/items/{item['id']}/cancel",json={'version':current['version']}).json()
    assert cancelled['items'][0]['state']=='cancelled'
    assert not prepare(client,cancelled)['results'][0]['ok']


def test_partial_failure_and_mixed_concessions(client):
    batch=create_batch(client,'two Market, one shakti Lake, three unknown')
    batch=complete(client,batch,batch['items'][0])
    batch=complete(client,batch,batch['items'][1],'shakti-demo')
    result=prepare(client,batch)
    assert [r['ok'] for r in result['results']]==[True,True,False]
    regular,concession=result['batch']['items'][:2]
    assert concession['ticket']['total_paise']==0
    t=regular['ticket'];t=action(client,t,'verify',payment_collected=True,concession_verified=False).json()
    t=action(client,t,'approve',confirmed=True,conductor_name='Demo').json()
    assert t['state']=='approved'
    assert action(client,concession['ticket'],'approve',confirmed=True,conductor_name='Demo').status_code==409
    assert client.get(f"/api/batches/{batch['id']}").json()['items'][0]['state']=='approved'
    with database() as db:
        url=str(db.bind.url)
    reopened=make_engine(url)
    with sessionmaker(reopened)() as db:
        saved=db.get(TicketBatch,batch['id'])
        assert len(saved.items)==3
        assert saved.original_transcription==batch['original_transcription']
    reopened.dispose()


def test_concurrent_prepare_and_approval(client):
    batch=create_batch(client,'two Market')
    batch=complete(client,batch,batch['items'][0])
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:prepare(client,batch),range(4)))
    ids=[r['batch']['items'][0]['ticket']['id'] for r in results]
    assert len(set(ids))==1
    t=results[0]['batch']['items'][0]['ticket'];t=action(client,t,'verify',payment_collected=True,concession_verified=False).json()
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses=list(pool.map(lambda _:action(client,t,'approve',confirmed=True,conductor_name='Demo'),range(4)))
    assert all(r.status_code==200 for r in responses)
    with database() as db:
        assert db.scalar(select(func.count()).select_from(SimulatedTicket))==1


def test_requested_example_separate_destinations(client):
    with database() as db:
        for stop_id, name in [(2,'Silk Board'),(3,'Jayanagar'),(5,'Majestic')]:
            db.get(Stop,stop_id).name=name
        db.commit()
    batch=create_batch(client,'Two Silk Board, one Jayanagar, three Majestic.')
    assert [i['draft']['destination_stop_id'] for i in batch['items']]==[2,3,5]
    assert [i['draft']['quantity'] for i in batch['items']]==[2,1,3]
    assert all(i['draft']['category'] is None for i in batch['items'])
