from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.core import exceptions, security
from app.repositories.api_keys import get_by_hash


def api_key_auth_dep(
    credentials: HTTPAuthorizationCredentials,
    db: Session,
) -> User:
    raw_key = credentials.credentials

    if not raw_key.startswith("lgp_"):
        raise exceptions.InvalidCredentialsError()

    key_hash = security.hash_api_key(raw_key)
    api_key = get_by_hash(key_hash, db)

    if api_key is None or not api_key.active:
        raise exceptions.InvalidCredentialsError()

    if not api_key.user.active:
        raise exceptions.InvalidCredentialsError()

    return api_key.user
