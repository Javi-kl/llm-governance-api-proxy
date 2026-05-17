import pytest
from unittest.mock import MagicMock
from fastapi import Request
from sqlalchemy.orm import Session

from app.core import security
from app.core.enums import UserRole
from app.core.exceptions import InvalidCredentialsError, PermissionDeniedError
from app.db.models.user import User
from app.dependencies.auth_dep import auth_dep, require_admin


# ── auth_dep ──────────────────────────────────────────────


def test_given_valid_token_then_returns_user(
    db_session: Session, admin_user: User
):
    token = security.create_access_token(admin_user.id, UserRole.ADMIN)
    request = MagicMock(spec=Request)
    request.cookies = {"access_token": token}

    result = auth_dep(request, db_session)

    assert result.username == "admin"
    assert result.role == UserRole.ADMIN


def test_given_no_token_then_raises_invalid_credentials(db_session: Session):
    request = MagicMock(spec=Request)
    request.cookies = {}

    with pytest.raises(InvalidCredentialsError):
        auth_dep(request, db_session)


def test_given_expired_token_then_raises_invalid_credentials(
    db_session: Session, admin_user: User
):
    from datetime import timedelta

    token = security.create_access_token(
        admin_user.id, UserRole.ADMIN, expires_delta=timedelta(seconds=-1)
    )
    request = MagicMock(spec=Request)
    request.cookies = {"access_token": token}

    with pytest.raises(InvalidCredentialsError):
        auth_dep(request, db_session)


# ── require_admin ─────────────────────────────────────────


def test_given_admin_user_then_returns_user(
    db_session: Session, admin_user: User
):
    token = security.create_access_token(admin_user.id, UserRole.ADMIN)
    request = MagicMock(spec=Request)
    request.cookies = {"access_token": token}

    result = require_admin(request, db_session)

    assert result.role == UserRole.ADMIN


def test_given_regular_user_then_raises_permission_denied(
    db_session: Session, regular_user: User
):
    token = security.create_access_token(regular_user.id, UserRole.USER)
    request = MagicMock(spec=Request)
    request.cookies = {"access_token": token}

    with pytest.raises(PermissionDeniedError):
        require_admin(request, db_session)
