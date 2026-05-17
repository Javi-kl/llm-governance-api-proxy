import pytest
from sqlalchemy.orm import Session

from app.core import security
from app.core.enums import UserRole
from app.db.models.user import User
from app.repositories import users


def test_given_users_in_db_then_returns_only_normal_users(
    db_session: Session, admin_user: User, regular_user: User
):
    result_users, total = users.get_all_normal_users(db_session)

    assert total == 1
    assert len(result_users) == 1
    assert result_users[0].role == UserRole.USER
    assert result_users[0].username == "testuser"


def test_given_empty_db_then_returns_empty_list_and_zero(db_session: Session):
    result_users, total = users.get_all_normal_users(db_session)

    assert total == 0
    assert result_users == []


def _create_n_users(db_session: Session, n: int) -> None:
    """Helper: crea N usuarios normales para tests de paginación."""
    for i in range(n):
        users.create(f"user{i}", security.hash_credential("12345"), db_session)
    db_session.commit()


@pytest.mark.parametrize(
    "offset, limit, expected_count",
    [(1, 1, 1), (0, 2, 2)],
    ids=["offset=1_limit=1", "offset=0_limit=2"],
)
def test_given_offset_and_limit_then_paginates_correctly(
    db_session: Session, offset: int, limit: int, expected_count: int
):
    _create_n_users(db_session, 3)

    result_users, total = users.get_all_normal_users(
        db_session, offset=offset, limit=limit
    )

    assert total == 3
    assert len(result_users) == expected_count

