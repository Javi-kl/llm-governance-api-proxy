import pytest
from pydantic import SecretStr

from app.core.bootstrap import bootstrap_admin
from app.core.enums import UserRole
from app.repositories import users


def test_bootstrap_admin_given_existing_admin_then_does_nothing(db_session):
    users.create("admin", "fake_hash", db_session, role=UserRole.ADMIN)
    db_session.commit()

    bootstrap_admin(db_session, SecretStr("valid12345"))

    admin_count = len(db_session.query(users.User).filter_by(role=UserRole.ADMIN).all())
    assert admin_count == 1


def test_bootstrap_admin_given_empty_password_then_raises_runtime_error(db_session):
    with pytest.raises(RuntimeError, match="BOOTSTRAP_ADMIN_PASSWORD no está definida"):
        bootstrap_admin(db_session, SecretStr(""))


def test_bootstrap_admin_given_weak_password_then_raises_value_error(db_session):
    with pytest.raises(ValueError):
        bootstrap_admin(db_session, SecretStr("123"))


def test_bootstrap_admin_given_valid_password_then_creates_admin(db_session):
    bootstrap_admin(db_session, SecretStr("ValidPass123!"))

    admin = users.exists_admin(db_session)
    assert admin is not None
    assert admin.username == "admin"
    assert admin.role == UserRole.ADMIN
