import pytest
from unittest.mock import MagicMock
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core import security
from app.core.enums import UserRole
from app.core.exceptions import InvalidCredentialsError, PasswordReuseError
from app.db.models.user import User
from app.schemas.user import ChangePasswordRequest
from app.services.admin_auth import login, change_password, logout


# ── login ─────────────────────────────────────────────────


def test_given_valid_credentials_then_returns_success_message(
    db_session: Session, admin_user: User, mock_response: MagicMock
):
    form = MagicMock(spec=OAuth2PasswordRequestForm)
    form.username = "admin"
    form.password = "admin12345"

    result = login(form, db_session, mock_response)

    assert result.message == "login correcto"
    mock_response.set_cookie.assert_called_once()


def test_given_nonexistent_user_then_raises_invalid_credentials(
    db_session: Session, mock_response: MagicMock
):
    form = MagicMock(spec=OAuth2PasswordRequestForm)
    form.username = "ghost"
    form.password = "whatever"

    with pytest.raises(InvalidCredentialsError):
        login(form, db_session, mock_response)


def test_given_wrong_password_then_raises_invalid_credentials(
    db_session: Session, admin_user: User, mock_response: MagicMock
):
    form = MagicMock(spec=OAuth2PasswordRequestForm)
    form.username = "admin"
    form.password = "wrong_password"

    with pytest.raises(InvalidCredentialsError):
        login(form, db_session, mock_response)


def test_given_non_admin_user_then_raises_invalid_credentials(
    db_session: Session, regular_user: User, mock_response: MagicMock
):
    form = MagicMock(spec=OAuth2PasswordRequestForm)
    form.username = "testuser"
    form.password = "123456"

    with pytest.raises(InvalidCredentialsError):
        login(form, db_session, mock_response)


# ── change_password ───────────────────────────────────────


def test_given_valid_change_then_updates_password(
    db_session: Session, admin_user: User
):
    password_data = ChangePasswordRequest(
        current_password="admin12345",
        new_password="NewSecure123!",
        confirm_password="NewSecure123!",
    )

    result = change_password(admin_user, password_data, db_session)

    assert result.message == "Contraseña actualizada correctamente"


def test_given_wrong_current_password_then_raises_invalid_credentials(
    db_session: Session, admin_user: User
):
    password_data = ChangePasswordRequest(
        current_password="wrong_password",
        new_password="NewSecure123!",
        confirm_password="NewSecure123!",
    )

    with pytest.raises(InvalidCredentialsError):
        change_password(admin_user, password_data, db_session)


def test_given_same_password_then_raises_password_reuse(
    db_session: Session
):
    from app.repositories import users as users_repo

    strong_pass = "MiP@ssw0rdSegura2024!"
    credential_hash = security.hash_credential(strong_pass)
    admin = users_repo.create("admin_reuse", credential_hash, db_session, role=UserRole.ADMIN)
    db_session.commit()

    password_data = ChangePasswordRequest(
        current_password=strong_pass,
        new_password=strong_pass,
        confirm_password=strong_pass,
    )

    with pytest.raises(PasswordReuseError):
        change_password(admin, password_data, db_session)


# ── logout ────────────────────────────────────────────────


def test_given_valid_user_then_deletes_cookie(
    admin_user: User, mock_response: MagicMock
):
    result = logout(mock_response, admin_user)

    assert result.message == "sesión cerrada"
    mock_response.delete_cookie.assert_called_once_with(
        key="access_token", path="/"
    )
