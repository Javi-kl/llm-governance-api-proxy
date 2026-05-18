import pytest
from sqlalchemy.orm import Session

from app.core import security
from app.core.enums import UserRole
from app.core.exceptions import InvalidCredentialsError, PasswordReuseError
from app.db.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest
from app.services.auth import change_password, login

# ── login ─────────────────────────────────────────────────


def test_given_nonexistent_user_then_raises_invalid_credentials(
    db_session: Session):
    login_data = LoginRequest(username="ghost", credential="123456")

    with pytest.raises(InvalidCredentialsError):
        login(login_data, db_session)


def test_given_wrong_credential_then_raises_invalid_credentials(
    db_session: Session, regular_user: User):
    login_data = LoginRequest(username="testuser", credential="999999")

    with pytest.raises(InvalidCredentialsError):
        login(login_data, db_session)


def test_given_inactive_user_then_raises_invalid_credentials(
    db_session: Session, regular_user: User):
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


