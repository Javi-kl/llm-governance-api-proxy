from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models.refresh_token import RefreshToken


def create(
    user_id: int, token_hash: str, expires_at: datetime, db: Session
) -> RefreshToken:
    """Inserta un nuevo refresh token en BD."""
    token = RefreshToken(
        user_id=user_id, token_hash=token_hash, expires_at=expires_at
    )
    db.add(token)
    db.flush()
    return token


def get_by_hash(token_hash: str, db: Session) -> RefreshToken | None:
    """Busca un refresh token por su hash."""
    return db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).scalar_one_or_none()


def revoke(token: RefreshToken, db: Session) -> None:
    """Marca un refresh token como revocado."""
    token.revoked = True
    db.flush()


def revoke_all_for_user(user_id: int, db: Session) -> None:
    """Revoca TODOS los refresh tokens de un usuario."""
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked == False)
        .values(revoked=True)
    )
    db.flush()
