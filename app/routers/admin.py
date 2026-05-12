from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import UserAlreadyExistsError
from app.db.database import get_db
from app.db.models.user import User
from app.dependencies.auth_dep import auth_dep
from app.schemas.user import UserCreate, UserResponse
from app.services import admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(auth_dep)],
):
    try:
        return admin.register(user_data, db)
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este username ya está registrado",
        )
