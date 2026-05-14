from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.db.models.user import User


def create(
    username: str, credential_hash: str, db: Session, role: UserRole = UserRole.USER
) -> User:
    user = User(username=username, credential_hash=credential_hash, role=role)
    db.add(user)
    db.flush()
    return user


def get_by_username(username: str, db: Session) -> User | None:
    return db.execute(
        select(User).where(User.username == username)
    ).scalar_one_or_none()


def exists_admin(db: Session) -> User | None:
    return db.execute(
        select(User).where(User.role == UserRole.ADMIN)
    ).scalar_one_or_none()


def update_password(user: User, password_hash: str, db: Session) -> None:
    user.credential_hash = password_hash
    db.flush()


def get_all_normal_users(
    db: Session, offset: int = 0, limit: int = 50
) -> tuple[list[User], int]:
    """Devuelve usuarios con role=USER y el total. Soporta paginación."""
    base_query = select(User).where(User.role == UserRole.USER)

    total = db.execute(
        select(func.count()).select_from(base_query.subquery())
    ).scalar_one()

    result_users = db.execute(
        base_query.offset(offset).limit(limit)
    ).scalars().all()

    return result_users, total
