import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import (
    CannotDeactivateAdminError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.db.models.user import User
from app.schemas.user import UserCreate
from app.services import admin
from app.services.admin import register


# ── register ──────────────────────────────────────────────


def test_given_valid_data_then_returns_user_response(db_session: Session):
    user_data = UserCreate(username="newuser", pin="12345")

    result = register(user_data, db_session)

    assert result.username == "newuser"
    assert result.id is not None


def test_given_duplicate_username_then_raises_user_already_exists(
    db_session: Session, regular_user: User
):
    user_data = UserCreate(username="testuser", pin="12345")

    with pytest.raises(UserAlreadyExistsError):
        register(user_data, db_session)


# ── deactivate_user ───────────────────────────────────────


def test_given_active_user_then_deactivates(
    db_session: Session, regular_user: User
):
    result = admin.deactivate_user(regular_user.id, db_session)

    assert result.message == "Usuario desactivado."
    db_session.refresh(regular_user)
    assert regular_user.active is False


def test_given_inactive_user_then_returns_already_deactivated(
    db_session: Session, regular_user: User
):
    regular_user.active = False
    db_session.commit()

    result = admin.deactivate_user(regular_user.id, db_session)

    assert result.message == "El usuario ya estaba desactivado."


def test_given_nonexistent_user_then_raises_user_not_found(db_session: Session):
    with pytest.raises(UserNotFoundError):
        admin.deactivate_user(9999, db_session)


def test_given_admin_user_then_raises_cannot_deactivate(
    db_session: Session, admin_user: User
):
    with pytest.raises(CannotDeactivateAdminError):
        admin.deactivate_user(admin_user.id, db_session)
