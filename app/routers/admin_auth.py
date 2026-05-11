from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models.user import User
from app.dependencies.auth_dep import auth_dep
from app.schemas.common import MessageResponse
from app.services import admin_auth

router = APIRouter(prefix="/admin/auth", tags=["admin_auth"])


@router.post("/login", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def login(
    response: Response,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:

    return admin_auth.login(form, db, response)


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
def logout(
    response: Response,
    request: Request,
    current_user: Annotated[User, Depends(auth_dep)],
) -> MessageResponse:

    return admin_auth.logout(response, current_user)
