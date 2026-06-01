import logging

import jwt
from fastapi import Depends, Request
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.core import config, exceptions, enums
from app.db.database import get_db
from app.db.models.user import User
from app.repositories import users

logger = logging.getLogger("auth_service")


def auth_dep(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        logger.warning("Token no válido")
        raise exceptions.InvalidCredentialsError()
    try:
        payload = jwt.decode(
            token,
            config.get_settings().SECRET_KEY.get_secret_value(),
            algorithms=[config.get_settings().ALGORITHM],
        )
        user_id = int(payload.get("sub", 0))

    except (InvalidTokenError, ValueError):
        raise exceptions.InvalidCredentialsError()

    user = users.get_by_id(user_id, db)

    if user is None or not user.active:
        raise exceptions.InvalidCredentialsError()

    return user


def require_admin(request: Request, db: Session = Depends(get_db)) -> User:
    """Autentica solo admins."""
    user = auth_dep(request, db)
    if user.role != enums.UserRole.ADMIN:
        raise exceptions.PermissionDeniedError()  # 403
    return user
