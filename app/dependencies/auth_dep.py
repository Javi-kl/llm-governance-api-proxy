"""Dependencias FastAPI: auth_dep extrae el usuario del JWT en cookie;
require_admin añade verificación de rol.

get_user_from_request() es la función base reutilizable por contextos
que no pueden usar Depends (Gradio, scripts, etc.).
"""

import logging

import jwt
from fastapi import Depends, Request
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.core import config, enums, exceptions
from app.db.database import get_db
from app.db.models.user import User
from app.repositories import users

logger = logging.getLogger("auth_service")


def get_user_from_request(request: Request, db: Session) -> User:
    """
    Lanza InvalidCredentialsError si la cookie falta, el token es inválido,
    el usuario no existe o está inactivo.
    """
    token = request.cookies.get("access_token")
    if not token:
        logger.warning("Token no válido")
        raise exceptions.InvalidCredentialsError()
    try:
        payload = jwt.decode(
            token,
            config.get_settings().SECRET_KEY.get_secret_value(),
            algorithms=[config.JWT_ALGORITHM],
        )
        user_id = int(payload.get("sub", 0))
    except (InvalidTokenError, ValueError):
        raise exceptions.InvalidCredentialsError()

    user = users.get_by_id(user_id, db)

    if user is None or not user.active:
        raise exceptions.InvalidCredentialsError()

    return user


def auth_dep(request: Request, db: Session = Depends(get_db)) -> User:
    """Dependencia FastAPI que reutiliza get_user_from_request."""
    return get_user_from_request(request, db)


def require_admin(request: Request, db: Session = Depends(get_db)) -> User:
    user = auth_dep(request, db)
    if user.role != enums.UserRole.ADMIN:
        raise exceptions.PermissionDeniedError()  # 403
    return user
