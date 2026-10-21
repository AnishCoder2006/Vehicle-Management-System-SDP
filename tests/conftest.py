
import os
from pathlib import Path

# Configure the test database BEFORE importing app.database or app.main.
TEST_DB_PATH = Path(__file__).resolve().parent.parent / ".pytest_vehicle_service.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
import app.models  # Register all SQLAlchemy models
from app.main import app


@pytest.fixture()
def db():
    """Give each test a clean database schema."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db):
    """Provide a FastAPI client backed by the test database."""
    with TestClient(app) as test_client:
        yield test_client
