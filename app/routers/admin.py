from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core import exceptions
from app.db.database import get_db
from app.db.models.user import User
from app.dependencies.auth_dep import require_admin
from app.schemas.user import UserCreate, UserListResponse, UserResponse
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


@router.get(
    "/users",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
)
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    return admin.list_users(db, offset=offset, limit=limit)

