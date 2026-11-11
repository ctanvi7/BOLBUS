import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db, make_engine
from app.main import app
from app.services.seed import seed_demo


@pytest.fixture
def client(tmp_path):
    engine = make_engine(f'sqlite:///{tmp_path}/test.db')
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions() as db:
        seed_demo(db)
    def override():
        with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = override
    # Use the isolated engine already seeded above, without the global lifespan.
    yield TestClient(app)
    app.dependency_overrides.clear()
    engine.dispose()
