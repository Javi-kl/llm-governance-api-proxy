from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.user import User


class UserRepository:
    @staticmethod
    def create(username: str, password_hash: str, db: Session) -> User:
        user = User(username=username, password_hash=password_hash)
        db.add(user)
        db.flush()
        return user

    @staticmethod
    def get_by_username(username: str, db: Session) -> User | None:
        return db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()
