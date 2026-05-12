import logging

from fastapi import Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core import config, enums, exceptions, security
from app.db.models.user import User
from app.repositories import users
from app.schemas.common import MessageResponse
from app.schemas.user import ChangePasswordRequest

logger = logging.getLogger("auth_service")


def login(
    form: OAuth2PasswordRequestForm, db: Session, response: Response
) -> MessageResponse:
    user = users.get_by_username(form.username, db)

    if not user:
        logger.warning("Login fallido para: %s", form.username)
        raise exceptions.InvalidCredentialsError()

    if user.role != enums.UserRole.ADMIN:
        logger.warning("Login fallido: usuario no es admin: %s", form.username)
        raise exceptions.InvalidCredentialsError()

    if not security.verify_password(form.password, user.credential_hash):
        logger.warning("Login fallido para: %s", form.username)
        raise exceptions.InvalidCredentialsError()

    token = security.create_access_token(
        subject=str(user.username), role=enums.UserRole.ADMIN
    )

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
    
    if not security.verify_password(password_data.current_password, user.credential_hash):
        logger.warning("Cambio de contraseña fallido: contraseña actual incorrecta para: %s", user.username)
        raise exceptions.InvalidCredentialsError()
        
    if password_data.current_password == password_data.new_password:
        raise exceptions.PasswordReuseError()
        
    users.update_password(user, security.hash_credential(password_data.new_password), db)
    logger.info("Cambio de contraseña exitoso para: %s", user.username)
    return MessageResponse(message="Contraseña actualizada correctamente")
    
def logout(response: Response, current_user: User) -> MessageResponse:
    response.delete_cookie(
        key="access_token",
        path="/",
    )

    logger.info("Logout exitoso para: %s", current_user.username)
    return MessageResponse(message="sesión cerrada")
