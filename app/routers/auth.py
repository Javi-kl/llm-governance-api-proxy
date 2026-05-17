from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.exceptions import PasswordReuseError
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
    return auth.login(login_data, db, response)


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
    try:
        return auth.change_password(user, password_data, db)
    except PasswordReuseError:
        raise HTTPException(
            status_code=400, detail="La nueva contraseña no puede ser igual a la actual"
        )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
def logout(
    response: Response,
    current_user: Annotated[User, Depends(auth_dep)],
) -> MessageResponse:
    return auth.logout(response, current_user)
