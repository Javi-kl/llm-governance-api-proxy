import logging

import jwt
from fastapi import Depends, Request
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.core import config, exceptions
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
        user_name = payload.get("sub", "")

    except (InvalidTokenError, ValueError):
        raise exceptions.InvalidCredentialsError()

    user = users.get_by_username(user_name, db)

    if user is None or not user.active:
        raise exceptions.InvalidCredentialsError()

    return user