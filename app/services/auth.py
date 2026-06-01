import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core import config, exceptions, security
from app.db.models.user import User
from app.repositories import refresh_tokens as refresh_repo
from app.repositories import users
from app.schemas.auth import ChangePasswordRequest, LoginRequest

logger = logging.getLogger("auth_service")


# ── Helper privado ───────────────────────────────────────────────


def _issue_token_pair(user: User, db: Session) -> tuple[str, str]:
    """Crea access + refresh token, guarda el refresh en BD, devuelve ambos."""
    settings = config.get_settings()

    access_token = security.create_access_token(subject=user.id, role=user.role)

    refresh_token = security.create_refresh_token()
    token_hash = security.hash_token(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    refresh_repo.create(user.id, token_hash, expires_at, db)

    return access_token, refresh_token


# ── Funciones públicas ────────────────────────────────────────────


def login(login_data: LoginRequest, db: Session) -> tuple[str, str]:
    """Login unificado. Devuelve (access_token, refresh_token)."""
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

    logger.info("Login exitoso para: %s", user.username)
    return _issue_token_pair(user, db)


def refresh(refresh_token: str | None, db: Session) -> tuple[str, str]:
    """Renueva el par de tokens usando un refresh token válido."""
    if not refresh_token:
        logger.warning("Refresh sin token en cookie")
        raise exceptions.InvalidCredentialsError()

    token_hash = security.hash_token(refresh_token)
    stored = refresh_repo.get_by_hash(token_hash, db)

    if not stored or stored.revoked:
        logger.warning("Refresh token inválido o revocado")
        raise exceptions.InvalidCredentialsError()

    expires_at = stored.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        logger.warning("Refresh token expirado para user_id: %s", stored.user_id)
        raise exceptions.InvalidCredentialsError()

    user = stored.user
    if not user.active:
        logger.warning("Refresh fallido: usuario inactivo: %s", user.username)
        refresh_repo.revoke(stored, db)
        raise exceptions.InvalidCredentialsError()

    refresh_repo.revoke(stored, db)

    logger.info("Refresh exitoso para: %s", user.username)
    return _issue_token_pair(user, db)


def logout(current_user: User, refresh_token: str | None, db: Session) -> None:
    """Cierra sesión: revoca el refresh token si existe."""
    if refresh_token:
        token_hash = security.hash_token(refresh_token)
        stored = refresh_repo.get_by_hash(token_hash, db)
        if stored:
            refresh_repo.revoke(stored, db)

    logger.info("Logout exitoso para: %s", current_user.username)


def change_password(
    user: User,
    password_data: ChangePasswordRequest,
    db: Session,
) -> None:
    """Cambia la contraseña y revoca todos los refresh tokens del usuario."""
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
    refresh_repo.revoke_all_for_user(user.id, db)
    logger.info("Cambio de contraseña exitoso para: %s", user.username)
