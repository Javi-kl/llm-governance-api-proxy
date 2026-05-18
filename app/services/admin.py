from sqlalchemy.orm import Session

from app.core import enums, exceptions, security
from app.db.models.user import User
from app.repositories import users
from app.schemas.auth import UserPinResetRequest

from app.schemas.user import (
    UserCreate,
    UserListResponse,
    UserResponse,
)


def register(user_data: UserCreate, db: Session) -> UserResponse:
    existing_user = users.get_by_username(user_data.username, db)
    if existing_user:
        raise exceptions.UserAlreadyExistsError(user_data.username)

    credential_hash = security.hash_credential(user_data.pin)
    user = users.create(user_data.username, credential_hash, db)
    return UserResponse.model_validate(user)


def list_users(db: Session, offset: int = 0, limit: int = 50) -> UserListResponse:
    """Lista usuarios normales con paginación."""
    result_users, total = users.get_all_normal_users(db, offset=offset, limit=limit)
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in result_users],
        total=total,
    )


def deactivate_user(user_id: int, db: Session) -> None:
    user = _get_normal_active_user_or_raise(user_id, db)
    users.deactivate_user(user, db)


def reset_user_pin(
    user_id: int, user_pin: UserPinResetRequest, db: Session
) -> None:
    user = _get_normal_active_user_or_raise(user_id, db)
    users.reset_user_pin(user, security.hash_credential(user_pin.pin), db)


def _get_normal_active_user_or_raise(user_id: int, db: Session) -> User:
    """Devuelve un usuario normal y activo. Lanza si no existe, es admin o está inactivo."""

    user = users.get_by_id(user_id, db)
    if not user:
        raise exceptions.UserNotFoundError(user_id)
    if user.role == enums.UserRole.ADMIN:
        raise exceptions.CannotModifyAdminError()
    if not user.active:
        raise exceptions.InactiveUserError()
    return user
