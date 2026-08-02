import logging

from sqlalchemy.orm import Session
from app.core.security import generate_api_key, hash_api_key
from app.repositories import api_keys, users
from app.core import exceptions


logger = logging.getLogger("api_keys_service")


def create_for_user(username: str, key_name: str, db: Session) -> str:
    user = users.get_by_username(username, db)

    if user is None:
        raise exceptions.UserNotFoundError(username)

    if not user.active:
        raise exceptions.InactiveUserError()

    if not 1 <= len(key_name) <= 100:
        raise ValueError

    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    prefix = raw_key[:12]

    api_keys.create(user.id, key_name, prefix, key_hash, db)

    logger.info("api key creada correctamente para: %s", user.username)
    return raw_key
