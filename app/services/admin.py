from sqlalchemy.orm import Session

from app.core import exceptions, security
from app.repositories import users
from app.schemas.user import UserCreate, UserListResponse, UserResponse


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
