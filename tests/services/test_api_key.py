import pytest
from sqlalchemy.orm import Session

from app.core import exceptions, security
from app.db.models.user import User
from app.services.api_keys import create_for_user
from app.repositories.api_keys import get_by_hash


def test_given_nonexistent_user_then_raises_not_found_error(db_session: Session):

    with pytest.raises(exceptions.UserNotFoundError):
        create_for_user("usuario_inexistente", "mi clave", db_session)


def test_given_nonactive_user_then_raises_inactive_user_error(
    regular_user: User, db_session: Session
):

    regular_user.active = False
    db_session.commit()

    with pytest.raises(exceptions.InactiveUserError):
        create_for_user(regular_user.username, "mi clave", db_session)


@pytest.mark.parametrize(
    "key_name",
    ["", "x" * 101],
)
def test_given_invalid_key_name__then_raise_valueerror(
    key_name: str, regular_user: User, db_session: Session
):

    with pytest.raises(ValueError):
        create_for_user(regular_user.username, key_name, db_session)


def test_given_valid_user_then_creates_api_key(regular_user: User, db_session: Session):
    raw_key = create_for_user(
        regular_user.username,
        "integration test",
        db_session,
    )
    stored_key = get_by_hash(
        security.hash_api_key(raw_key),
        db_session,
    )

    assert raw_key.startswith("lgp_")
    assert stored_key is not None
    assert stored_key.user_id == regular_user.id
    assert stored_key.name == "integration test"
    assert stored_key.prefix == raw_key[:12]
    assert stored_key.key_hash != raw_key
    assert stored_key.active is True
