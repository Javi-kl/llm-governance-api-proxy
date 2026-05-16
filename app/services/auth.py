import logging

from fastapi import Response
from sqlalchemy.orm import Session

from app.core import config, exceptions, security
from app.db.models.user import User
from app.repositories import users
from app.schemas.auth import ChangePasswordRequest, LoginRequest
from app.schemas.common import MessageResponse

logger = logging.getLogger("auth_service")


def login(login_data: LoginRequest, db: Session, response: Response) -> MessageResponse:
    user = users.get_by_username(login_data.username, db)

    if not user:
        logger.warning("Login fallido para: %s", login_data.username)
        raise exceptions.InvalidCredentialsError()

    if not user.active:
        logger.warning("Login fallido: usuario inactivo: %s", login_data.username)
        raise exceptions.InvalidCredentialsError()

    if not security.verify_password(login_data.credential, user.credential_hash):
        logger.warning("Login fallido para: %s", login_data.username)
        raise exceptions.InvalidCredentialsError()

    token = security.create_access_token(subject=user.id, role=user.role)

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=config.get_settings().ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=config.get_settings().COOKIE_SECURE,
        samesite="lax",
        path="/",
    )

    logger.info("Login exitoso para: %s", user.username)
    return MessageResponse(message="login correcto")


def change_password(
    user: User,
    password_data: ChangePasswordRequest,
    db: Session,
) -> MessageResponse:
    if not security.verify_password(
        password_data.current_password, user.credential_hash
    ):
        logger.warning(
            "Cambio de contraseña fallido: contraseña actual incorrecta para: %s",
            user.username,
        )
        raise exceptions.InvalidCredentialsError()

    if password_data.current_password == password_data.new_password:
        raise exceptions.PasswordReuseError()

    users.update_password(
        user, security.hash_credential(password_data.new_password), db
    )
    logger.info("Cambio de contraseña exitoso para: %s", user.username)
    return MessageResponse(message="Contraseña actualizada correctamente")


def logout(response: Response, current_user: User) -> MessageResponse:
    response.delete_cookie(
        key="access_token",
        path="/",
    )

    logger.info("Logout exitoso para: %s", current_user.username)
    return MessageResponse(message="sesión cerrada")
