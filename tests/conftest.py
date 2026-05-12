from datetime import timedelta
from typing import Generator
from unittest.mock import MagicMock

import pytest
from fastapi import Request, Response
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core import security
from app.core.enums import UserRole
from app.db.database import Base, get_db
from app.db.models.user import User
from app.main import app
from app.repositories import users

# Engine de test: SQLite en memoria, se destruye al cerrar el proceso
test_engine = create_engine("sqlite:///:memory:", echo=False)
TestSessionLocal = sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Crea tablas en SQLite y devuelve una sesión limpia.
    Al terminar el test, hace rollback para que el siguiente test empiece desde cero."""
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient que intercepta get_db() → usa la sesión de test, no PostgreSQL."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_response() -> MagicMock:
    """Mock de Response de FastAPI. Simula set_cookie() y delete_cookie()."""
    return MagicMock(spec=Response)


@pytest.fixture
def mock_request():
    """Mock de Request con .cookies como dict configurable."""
    req = MagicMock(spec=Request)
    req.cookies = {}
    return req


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Crea un admin en la BD de test y lo devuelve."""
    credential_hash = security.hash_credential("admin12345")
    user = users.create("admin", credential_hash, db_session, role=UserRole.ADMIN)
    db_session.commit()
    return user


@pytest.fixture
def regular_user(db_session):
    """Crea un usuario normal en la BD de test y lo devuelve."""
    credential_hash = security.hash_credential("123456")
    user = users.create("testuser", credential_hash, db_session, role=UserRole.USER)
    db_session.commit()
    return user


def create_token(
    subject: str, role: UserRole, expires_delta: timedelta | None = None
) -> str:
    return security.create_access_token(subject, role, expires_delta)
