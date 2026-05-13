import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import UserAlreadyExistsError
from app.db.models.user import User
from app.schemas.user import UserCreate
from app.services.admin import register


def test_given_valid_data_then_returns_user_response(db_session: Session):
    user_data = UserCreate(username="newuser", pin="12345")

    result = register(user_data, db_session)

    assert result.username == "newuser"
    assert result.id is not None


def test_given_duplicate_username_then_raises_user_already_exists(
    db_session: Session, regular_user: User
):
    user_data = UserCreate(username="testuser", pin="12345")

    with pytest.raises(UserAlreadyExistsError):
        register(user_data, db_session)
