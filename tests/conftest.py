from datetime import timedelta
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from limits.storage.memory import MemoryStorage
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import make_url

import app.db.models  # noqa: F401
from app.core import config, security
from app.core.enums import UserRole
from app.core.rate_limit import limiter
from app.db.database import Base, get_db
from app.db.models.user import User
from app.main import app
from app.repositories import users


def _assert_safe_test_database_url(test_url: str, app_url: str) -> None:
    if test_url == app_url:
        raise RuntimeError("TEST_DATABASE_URL no puede coincidir con DATABASE_URL.")

    db_name = make_url(test_url).database or ""
    if "test" not in db_name.lower():
        raise RuntimeError(
            "El nombre de la base de datos de test debe contener 'test'."
        )


# Engine de test: PostgreSQL (TEST_DATABASE_URL).
_test_db_url = config.get_settings().TEST_DATABASE_URL
if not _test_db_url:
    raise RuntimeError("TEST_DATABASE_URL no está configurada. Defínela en .env.")

_assert_safe_test_database_url(_test_db_url, config.get_settings().DATABASE_URL)

test_engine = create_engine(_test_db_url, echo=False)
TestSessionLocal = sessionmaker(bind=test_engine, expire_on_commit=False)


def _reset_test_schema() -> None:
    """Resetea el schema public de PostgreSQL para aislar cada test."""
    with test_engine.begin() as conn:
        # DROP SCHEMA CASCADE elimina también tipos enum como userrole.
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    Base.metadata.create_all(bind=test_engine)


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> Generator[None, None, None]:
    """Limpia el storage en memoria de SlowAPI antes de cada test."""
    storage = limiter._storage
    if isinstance(storage, MemoryStorage):
        storage.storage.clear()
    yield


@pytest.fixture
def db_session() -> Generator[Session, None, None]:

    _reset_test_schema()

    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        _reset_test_schema()


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
