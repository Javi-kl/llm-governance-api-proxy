from datetime import timedelta
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import security
from app.core.enums import UserRole
from app.core.rate_limit import limiter
from app.db.database import Base, get_db
from app.db.models.user import User
from app.main import app
from app.repositories import users

# Engine de test: SQLite en memoria compartido entre threads
test_engine = create_engine(
    "sqlite:///:memory:",
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> Generator[None, None, None]:
    """Limpia el storage en memoria de SlowAPI antes de cada test."""
    if limiter._storage is not None and hasattr(limiter._storage, "storage"):
        limiter._storage.storage.clear()
    yield


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Crea tablas en SQLite -> devuelve una sesión limpia -> borra las tablas."""
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    yield session
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient que intercepta get_db() → usa la sesión de test, no PostgreSQL."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with patch("app.main.bootstrap_admin"):
        with TestClient(app) as test_client:
            yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Crea un admin en la BD de test y lo devuelve."""
    credential_hash = security.hash_credential("admin12345")
    user = users.create("admin", credential_hash, db_session, role=UserRole.ADMIN)
    db_session.commit()
    return user


@pytest.fixture
def regular_user(db_session) -> User:
    """Crea un usuario normal en la BD de test y lo devuelve."""
    credential_hash = security.hash_credential("123456")
    user = users.create("testuser", credential_hash, db_session, role=UserRole.USER)
    db_session.commit()
    return user


def create_token(
    subject: int, role: UserRole, expires_delta: timedelta | None = None
) -> str:
    return security.create_access_token(subject, role, expires_delta)
