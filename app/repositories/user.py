from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.user import User, UserRole


class UserRepository:
    @staticmethod
    def create(
        username: str, credential_hash: str, db: Session, role: UserRole = UserRole.USER
    ) -> User:
        user = User(username=username, credential_hash=credential_hash, role=role)
        db.add(user)
        db.flush()
        return user

    @staticmethod
    def get_by_username(username: str, db: Session) -> User | None:
        return db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

    @staticmethod
    def exists_admin(db: Session) -> User | None:
        return db.execute(
            select(User).where(User.role == UserRole.ADMIN)
        ).scalar_one_or_none()
