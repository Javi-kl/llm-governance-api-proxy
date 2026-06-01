import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.core import security
from app.core.enums import UserRole
from app.core.exceptions import InvalidCredentialsError, PasswordReuseError
from app.db.models.user import User
from app.repositories import refresh_tokens as refresh_repo
from app.schemas.auth import ChangePasswordRequest, LoginRequest
from app.services.auth import change_password, login, refresh

# ── login ─────────────────────────────────────────────────


def test_given_nonexistent_user_then_raises_invalid_credentials(db_session: Session):
    login_data = LoginRequest(username="ghost", credential="123456")

    with pytest.raises(InvalidCredentialsError):
        login(login_data, db_session)


def test_given_wrong_credential_then_raises_invalid_credentials(
    db_session: Session, regular_user: User
):
    login_data = LoginRequest(username="testuser", credential="999999")

    with pytest.raises(InvalidCredentialsError):
        login(login_data, db_session)


def test_given_inactive_user_then_raises_invalid_credentials(
    db_session: Session, regular_user: User
):
    regular_user.active = False
    db_session.commit()

    login_data = LoginRequest(username="testuser", credential="123456")

    with pytest.raises(InvalidCredentialsError):
        login(login_data, db_session)


# ── change_password ───────────────────────────────────────


def test_given_valid_change_then_updates_password(
    db_session: Session, admin_user: User
):
    password_data = ChangePasswordRequest(
        current_password="admin12345",
        new_password="NewSecure123!",
        confirm_password="NewSecure123!",
    )

    change_password(admin_user, password_data, db_session)

    # Verificar efecto colateral: el hash de contraseña cambió
    assert security.verify_password("NewSecure123!", admin_user.credential_hash)


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


def test_given_same_password_then_raises_password_reuse(db_session: Session):
    from app.repositories import users as users_repo

    strong_pass = "MiP@ssw0rdSegura2024!"
    credential_hash = security.hash_credential(strong_pass)
    admin = users_repo.create(
        "admin_reuse", credential_hash, db_session, role=UserRole.ADMIN
    )
    db_session.commit()

    password_data = ChangePasswordRequest(
        current_password=strong_pass,
        new_password=strong_pass,
        confirm_password=strong_pass,
    )

    with pytest.raises(PasswordReuseError):
        change_password(admin, password_data, db_session)


# ── login (refresh token) ─────────────────────────────────


def test_given_valid_credentials_then_returns_token_pair(
    db_session: Session, regular_user: User
):
    login_data = LoginRequest(username="testuser", credential="123456")

    access, refresh = login(login_data, db_session)

    assert isinstance(access, str) and len(access) > 0
    assert isinstance(refresh, str) and len(refresh) == 128


# ── refresh ───────────────────────────────────────────────


def _create_refresh_token_for_user(user: User, db: Session, expires_at=None) -> str:
    """Helper: crea un refresh token en BD para un usuario."""
    if expires_at is None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    token = security.create_refresh_token()
    token_hash = security.hash_token(token)
    refresh_repo.create(user.id, token_hash, expires_at, db)
    db.commit()
    return token


def test_given_valid_refresh_token_then_rotates_and_returns_pair(
    db_session: Session, regular_user: User
):
    original_token = _create_refresh_token_for_user(regular_user, db_session)

    new_access, new_refresh = refresh(original_token, db_session)

    assert isinstance(new_access, str) and len(new_access) > 0
    assert isinstance(new_refresh, str) and len(new_refresh) == 128
    assert new_refresh != original_token  # rotación


def test_given_none_refresh_token_then_raises_invalid_credentials(
    db_session: Session,
):
    with pytest.raises(InvalidCredentialsError):
        refresh(None, db_session)


def test_given_revoked_refresh_token_then_raises_invalid_credentials(
    db_session: Session, regular_user: User
):
    token = _create_refresh_token_for_user(regular_user, db_session)

    stored = refresh_repo.get_by_hash(security.hash_token(token), db_session)
    refresh_repo.revoke(stored, db_session)
    db_session.commit()

    with pytest.raises(InvalidCredentialsError):
        refresh(token, db_session)


def test_given_expired_refresh_token_then_raises_invalid_credentials(
    db_session: Session, regular_user: User
):
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    token = _create_refresh_token_for_user(regular_user, db_session, expires_at=past)

    with pytest.raises(InvalidCredentialsError):
        refresh(token, db_session)
