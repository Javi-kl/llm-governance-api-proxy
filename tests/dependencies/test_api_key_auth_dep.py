import pytest

from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core import security
from app.repositories.api_keys import get_by_hash
from app.core.exceptions import InvalidCredentialsError
from app.db.models.user import User
from app.services.api_keys import create_for_user
from app.dependencies.api_key_auth_dep import api_key_auth_dep


def _bearer_credentials(raw_key: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=raw_key,
    )


def test_given_valid_api_key_then_returns_owner(
    regular_user: User,
    db_session: Session,
):
    raw_key = create_for_user(
        regular_user.username,
        "dependency test",
        db_session,
    )

    credentials = _bearer_credentials(raw_key)

    result = api_key_auth_dep(credentials, db_session)

    assert result.id == regular_user.id


def test_given_unknown_api_key_then_raises_invalid_credentials(
    db_session: Session,
):
    credentials = _bearer_credentials("lgp_clave_que_no_existe")

    with pytest.raises(InvalidCredentialsError):
        api_key_auth_dep(credentials, db_session)


def test_given_inactive_api_key_then_raises_invalid_credentials(
    regular_user: User,
    db_session: Session,
):
    raw_key = create_for_user(
        regular_user.username,
        "inactive key test",
        db_session,
    )

    stored_key = get_by_hash(security.hash_api_key(raw_key), db_session)

    assert stored_key is not None
    stored_key.active = False
    db_session.commit()

    with pytest.raises(InvalidCredentialsError):
        api_key_auth_dep(_bearer_credentials(raw_key), db_session)


def test_given_inactive_owner_then_raises_invalid_credentials(
    regular_user: User,
    db_session: Session,
):
    raw_key = create_for_user(
        regular_user.username,
        "inactive owner test",
        db_session,
    )

    regular_user.active = False
    db_session.commit()

    with pytest.raises(InvalidCredentialsError):
        api_key_auth_dep(_bearer_credentials(raw_key), db_session)


@pytest.mark.parametrize(
    "raw_key",
    [
        "sk-clave-externa",
        "Bearer lgp_incorrecta",
    ],
    ids=["wrong_prefix", "full_header"],
)
def test_given_invalid_api_key_format_then_raises_invalid_credentials(
    raw_key: str,
    db_session: Session,
):
    with pytest.raises(InvalidCredentialsError):
        api_key_auth_dep(_bearer_credentials(raw_key), db_session)
