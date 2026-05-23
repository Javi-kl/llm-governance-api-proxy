from datetime import timedelta
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
    settings = config.get_settings()
    access_token, refresh_token = auth.login(login_data, db)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=int(timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES).total_seconds()),
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()),
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/api/v1/auth",
    )

    return MessageResponse(message="login correcto")


@router.post(
    "/refresh",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
def refresh_token(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """Renueva el par de tokens usando el refresh token de la cookie."""
    settings = config.get_settings()
    refresh_token_value = request.cookies.get("refresh_token")

    new_access, new_refresh = auth.refresh(refresh_token_value, db)

    response.set_cookie(
        key="access_token",
        value=new_access,
        httponly=True,
        max_age=int(timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES).total_seconds()),
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        max_age=int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()),
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/api/v1/auth",
    )

    return MessageResponse(message="Tokens renovados correctamente")


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
    request: Request,
    response: Response,
    current_user: Annotated[User, Depends(auth_dep)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    refresh_token_value = request.cookies.get("refresh_token")

    response.delete_cookie(
        key="access_token",
        path="/",
    )
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
    )
    auth.logout(current_user, refresh_token_value, db)
    return MessageResponse(message="sesión cerrada")
