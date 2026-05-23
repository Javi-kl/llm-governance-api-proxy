from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models.user import User
from app.dependencies.auth_dep import require_admin
from app.schemas.common import MessageResponse
from app.schemas.user import (
    UserCreate,
    UserListResponse,
    UserResponse,
)
from app.schemas.auth import UserPinResetRequest
from app.services import admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/users/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
):
    return admin.register(user_data, db)


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


@router.patch(
    "/users/{user_id}/deactivate",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
def deactivate_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
):

    admin.deactivate_user(user_id, db)
    return MessageResponse(message="Usuario desactivado.")


@router.patch(
    "/users/{user_id}/pin",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
def reset_user_pin(
    user_id: int,
    user_pin: UserPinResetRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
):

    admin.reset_user_pin(user_id, user_pin, db)
    return MessageResponse(message="PIN de usuario modificado.")
