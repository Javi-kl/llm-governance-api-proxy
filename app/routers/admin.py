from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core import exceptions
from app.db.database import get_db
from app.db.models.user import User
from app.dependencies.auth_dep import require_admin
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
    _: Annotated[User, Depends(require_admin)],
):
    try:
        return admin.register(user_data, db)
    except exceptions.UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este username ya está registrado.",
        )