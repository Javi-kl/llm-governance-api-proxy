import logging

from sqlalchemy.orm import Session

from app.core import exceptions, security
from app.db.models.user import User
from app.repositories import users
from app.schemas.auth import ChangePasswordRequest, LoginRequest


logger = logging.getLogger("auth_service")


def login(login_data: LoginRequest, db: Session) -> str:
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

    logger.info("Login exitoso para: %s", user.username)
    return token


def change_password(
    user: User,
    password_data: ChangePasswordRequest,
    db: Session,
) -> None:
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


def logout(current_user: User, db: Session) -> None:
    # TODO Ahora: solo log. Después: revoke refresh tokens.
    logger.info("Logout exitoso para: %s", current_user.username)
    
