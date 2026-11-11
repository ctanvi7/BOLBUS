"""Local synthetic timing only: python scripts/benchmark_batches.py. No speech calls."""
import sys
import tempfile
import statistics
from pathlib import Path
from time import perf_counter
from uuid import uuid4
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from app.database import Base, make_engine, get_db, get_write_db
from app.main import app
from app.services.seed import seed_demo

with tempfile.TemporaryDirectory() as directory:
    engine = make_engine(f'sqlite:///{directory}/benchmark.db')
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions() as db:
        seed_demo(db)
    def read():
        with sessions() as db:
            yield db
    def write():
        with sessions() as db:
            db.execute(text('BEGIN IMMEDIATE'))
            yield db
    app.dependency_overrides[get_db] = read
    app.dependency_overrides[get_write_db] = write
    timings, walls = [], []
    try:
        client = TestClient(app)
        for _ in range(20):
            response = client.post('/api/batches', json={'client_batch_id':str(uuid4()),'route_id':1,
                'original_transcription':'Two Market, one College, three Lake',
                'items':[{'origin_stop_id':1,'destination_stop_id':destination,'quantity':quantity,'category':'standard'} for destination,quantity in [(2,2),(3,1),(5,3)]]})
            response.raise_for_status()
            batch=response.json()
            start=perf_counter()
            response=client.post(f"/api/batches/{batch['id']}/prepare",json={'versions':{i['id']:i['version'] for i in batch['items']}})
            response.raise_for_status()
            walls.append((perf_counter()-start)*1000)
            assert all(row['ok'] for row in response.json()['results'])
            timings.append(response.json()['processing_ms'])
        print({'batches':20,'items_per_batch':3,'server_median_ms':round(statistics.median(timings),2),
            'server_max_ms':round(max(timings),2),'testclient_roundtrip_median_ms':round(statistics.median(walls),2)})
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
