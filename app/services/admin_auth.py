import logging

from fastapi import Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core import enums, config, exceptions, security
from app.repositories.user import UserRepository
from app.schemas.common import MessageResponse
settings = config.get_settings()
logger = logging.getLogger("auth_service")


def login(form: OAuth2PasswordRequestForm, db: Session, response: Response) -> MessageResponse:
    user = UserRepository.get_by_username(form.username, db)

    if not user:
        logger.warning("Login fallido para: %s", form.username)
        raise exceptions.InvalidCredentialsError()
        
    if user.role != enums.UserRole.ADMIN:
        logger.warning("Login fallido: usuario no es admin: %s", form.username)
        raise exceptions.InvalidCredentialsError()
        
    if not security.verify_password(form.password, user.credential_hash):
        logger.warning("Login fallido para: %s", form.username)
        raise exceptions.InvalidCredentialsError()

    token = security.create_access_token(subject=str(user.username))

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )

    logger.info("Login exitoso para: %s", user.username)
    return MessageResponse(message="login correcto")