from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidCredentialsError
from app.db.database import get_db
from app.schemas.common import MessageResponse
from app.services import admin_auth

router = APIRouter(prefix="/admin/auth", tags=["admin_auth"])


@router.post("/login", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def login(
    response: Response,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    try:
        return admin_auth.login(form, db, response)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales no válidas",
        )