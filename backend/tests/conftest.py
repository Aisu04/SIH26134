import os
from uuid import UUID

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-with-sufficient-length-for-jwt-2025"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["FRONTEND_ORIGIN"] = "http://localhost:5173"

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Institution, Opportunity, User

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def set_user_role():
    def set_role(user_id: str, role: str) -> None:
        with TestingSessionLocal() as db:
            user = db.get(User, UUID(user_id))
            assert user is not None
            user.role = role
            db.commit()

    return set_role


@pytest.fixture
def set_opportunity_status():
    def set_status(opportunity_id: str, status: str) -> None:
        with TestingSessionLocal() as db:
            opportunity = db.get(Opportunity, UUID(opportunity_id))
            assert opportunity is not None
            opportunity.status = status
            db.commit()

    return set_status


@pytest.fixture
def create_institution():
    def create(name: str) -> str:
        with TestingSessionLocal() as db:
            institution = Institution(name=name, sector="Education")
            db.add(institution)
            db.commit()
            db.refresh(institution)
            return str(institution.id)

    return create


@pytest.fixture
def assign_user_institution():
    def assign(user_id: str, institution_id: str) -> None:
        with TestingSessionLocal() as db:
            user = db.get(User, UUID(user_id))
            assert user is not None
            user.institution_id = UUID(institution_id)
            db.commit()

    return assign


@pytest.fixture
def isolated_db():
    isolated_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=isolated_engine)
    isolated_session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=isolated_engine,
    )
    with isolated_session_factory() as db:
        yield db
    Base.metadata.drop_all(bind=isolated_engine)
    isolated_engine.dispose()


def client():
    with TestClient(app) as test_client:
        yield test_client


__all__ = ["client"]
