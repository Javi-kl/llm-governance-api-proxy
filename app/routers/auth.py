from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.cookies import set_auth_cookies, clear_auth_cookies
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

    access_token, refresh_token = auth.login(login_data, db)
    set_auth_cookies(response, access_token, refresh_token)

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

    refresh_token_value = request.cookies.get("refresh_token")
    new_access, new_refresh = auth.refresh(refresh_token_value, db)
    set_auth_cookies(response, new_access, new_refresh)

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

    clear_auth_cookies(response)
    auth.logout(current_user, refresh_token_value, db)
    return MessageResponse(message="sesión cerrada")
