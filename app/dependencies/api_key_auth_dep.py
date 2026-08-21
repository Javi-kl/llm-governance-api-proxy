from typing import Annotated

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.core import exceptions, security
from app.repositories.api_keys import get_by_hash
from app.db.database import get_db

bearer_scheme = HTTPBearer(auto_error=False)


def api_key_auth_dep(
    bearer_credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> User:

    if bearer_credentials is None:
        raise exceptions.InvalidCredentialsError()

    raw_key = bearer_credentials.credentials

    if not raw_key.startswith("lgp_"):
        raise exceptions.InvalidCredentialsError()

    key_hash = security.hash_api_key(raw_key)
    api_key = get_by_hash(key_hash, db)

    if api_key is None or not api_key.active:
        raise exceptions.InvalidCredentialsError()

    if not api_key.user.active:
        raise exceptions.InvalidCredentialsError()

    return api_key.user
