import pytest
from pydantic import ValidationError

from app.schemas.auth import ChangePasswordRequest
from app.schemas.user import UserCreate


def test_given_valid_pin_then_creates_user():
    user = UserCreate(username="testuser", pin="12345")

    assert user.username == "testuser"
    assert user.pin == "12345"


def test_given_invalid_pin_then_raises_error():
    with pytest.raises(ValidationError):
        UserCreate(username="testuser", pin="123")


def test_given_mismatched_passwords_then_raises_error():
    with pytest.raises(ValidationError, match="no coinciden"):
        ChangePasswordRequest(
            current_password="old_pass",
            new_password="NewSecure123!",
            confirm_password="DifferentPass123!",
        )
