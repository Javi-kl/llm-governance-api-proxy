from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core import config

from app.core.rate_limit import limiter
from app.db.database import get_db
from app.db.models.user import User
from app.dependencies.auth_dep import auth_dep, require_admin
from app.schemas.auth import ChangePasswordRequest, LoginRequest
from app.schemas.common import MessageResponse
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("5/5minute")
def login(
    request: Request,
    login_data: LoginRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """Login unificado para usuarios normales y administradores."""

    token = auth.login(login_data, db)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=config.get_settings().ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=config.get_settings().COOKIE_SECURE,
        samesite="lax",
        path="/",
    )

    return MessageResponse(message="login correcto")


@router.patch(
    "/password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("1/minute")
def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    auth.change_password(user, password_data, db)
    return MessageResponse(message="Contraseña actualizada correctamente")


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
def logout(
    response: Response,
    current_user: Annotated[User, Depends(auth_dep)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    response.delete_cookie(
        key="access_token",
        path="/",
    )
    auth.logout(current_user, db)
    return MessageResponse(message="sesión cerrada")
