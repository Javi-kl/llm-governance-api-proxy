import logging

from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.core.security import hash_credential, validate_password_strength
from app.db.models.user import UserRole
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)


def bootstrap_admin(db: Session, password: SecretStr) -> None:
    """Crea el primer admin si no existe."""
    if UserRepository.exists_admin(db):
        return

    if not password.get_secret_value():
        logger.error("No hay admin en BD y BOOTSTRAP_ADMIN_PASSWORD no está definida")
        raise RuntimeError(
            "No hay admin en BD y BOOTSTRAP_ADMIN_PASSWORD no está definida"
        )

    try:
        validate_password_strength(password.get_secret_value())
    except ValueError as e:
        logger.error("Bootstrap fallido: %s", e)
        raise

    credential_hash = hash_credential(password.get_secret_value())
    UserRepository.create("admin", credential_hash, db, role=UserRole.ADMIN)
