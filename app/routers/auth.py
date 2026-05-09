from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.exceptions import UserAlreadyExistsError
from app.db.database import get_db
from app.schemas.auth import UserCreate, UserResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(user_data: UserCreate, db: Annotated[Session, Depends(get_db)]):
    try:
        return AuthService.register(user_data, db)
    except UserAlreadyExistsError:
        # La recepción traduce el error de dominio al protocolo HTTP.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este username ya está registrado",
        )
