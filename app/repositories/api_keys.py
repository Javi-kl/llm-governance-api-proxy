from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models.api_key import ApiKey


def create(user_id: int, name: str, prefix: str, key_hash: str, db: Session) -> ApiKey:
    api_key = ApiKey(
        user_id=user_id,
        name=name,
        prefix=prefix,
        key_hash=key_hash,
    )

    db.add(api_key)
    db.flush()
    return api_key


def get_by_hash(key_hash: str, db: Session) -> ApiKey | None:
    return db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash)
    ).scalar_one_or_none()
