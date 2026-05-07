from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.repositories.user import UserRepository
from app.schemas.auth import UserCreate, UserResponse


class AuthService:
    @staticmethod
    def register(user_data: UserCreate, db: Session) -> UserResponse:
        existing_user = UserRepository.get_by_username(user_data.username, db)  # TODO
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este username ya está registrado",
            )
        password_hash = hash_password(user_data.password)  # TODO
        user = UserRepository.create(user_data.username, password_hash, db)
        return UserResponse.model_validate(user)
