from datetime import timedelta

import jwt
import pytest
from pydantic import HttpUrl, SecretStr, ValidationError

from app.core import config, security
from app.core.config import Settings
from app.core.enums import UserRole

# ── create_access_token ──────────────────────────────────


def test_create_access_token_given_valid_subject_then_returns_decodable_jwt():
    token = security.create_access_token(42, UserRole.USER)

    payload = jwt.decode(
        token,
        config.get_settings().SECRET_KEY.get_secret_value(),
        algorithms=[config.JWT_ALGORITHM],
        options={"verify_exp": False},
    )

    assert payload["sub"] == "42"
    assert payload["role"] == "user"


def test_create_access_token_given_custom_expiry_then_has_correct_exp_claim():
    token = security.create_access_token(
        42, UserRole.USER, expires_delta=timedelta(minutes=5)
    )

    payload = jwt.decode(
        token,
        config.get_settings().SECRET_KEY.get_secret_value(),
        algorithms=[config.JWT_ALGORITHM],
        options={"verify_exp": False},
    )

    delta = payload["exp"] - payload["iat"]
    assert delta == pytest.approx(300, abs=2)


def test_create_access_token_given_no_expiry_then_uses_default_60_minutes():
    token = security.create_access_token(42, UserRole.USER)

    payload = jwt.decode(
        token,
        config.get_settings().SECRET_KEY.get_secret_value(),
        algorithms=[config.JWT_ALGORITHM],
        options={"verify_exp": False},
    )

    delta = payload["exp"] - payload["iat"]
    expected = config.get_settings().ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert delta == pytest.approx(expected, abs=2)


# ── verify_password ──────────────────────────────────────


def test_verify_password_given_correct_password_then_returns_true():
    credential_hash = security.hash_credential("admin12345")
    assert security.verify_password("admin12345", credential_hash) is True


def test_verify_password_given_wrong_password_then_returns_false():
    credential_hash = security.hash_credential("admin12345")
    assert security.verify_password("wrong_password", credential_hash) is False


def test_verify_password_given_invalid_hash_then_returns_false():
    assert security.verify_password("anything", "no-es-un-hash-valido") is False


# ── validate_password_strength ───────────────────────────


def test_validate_password_strength_given_too_short_then_raises_value_error():
    with pytest.raises(ValueError, match="al menos 8 caracteres"):
        security.validate_password_strength("corta")


def test_validate_password_strength_given_weak_score_then_raises_value_error():
    with pytest.raises(ValueError, match="no es lo suficientemente segura"):
        security.validate_password_strength("12345678")


def test_validate_password_strength_given_strong_then_returns_password():
    result = security.validate_password_strength("MiP@ssw0rdSegura2024!")
    assert result == "MiP@ssw0rdSegura2024!"


# ── validate_pin ─────────────────────────────────────────


@pytest.mark.parametrize("valid_pin", ["12345", "123456"])
def test_validate_pin_given_valid_5_or_6_digits_then_returns(valid_pin):
    assert security.validate_pin(valid_pin) == valid_pin


@pytest.mark.parametrize("invalid_pin", ["1234", "1234567", "abcde", ""])
def test_validate_pin_given_invalid_format_then_raises_value_error(invalid_pin):

    with pytest.raises(ValueError, match="entre 5 y 6 dígitos"):
        security.validate_pin(invalid_pin)


# ── create_refresh_token ─────────────────────────────────


def test_create_refresh_token_returns_128_hex_chars():
    token = security.create_refresh_token()

    assert len(token) == 128
    assert all(c in "0123456789abcdef" for c in token)


# ── hash_token ───────────────────────────────────────────


def test_hash_token_given_same_input_then_returns_same_hash():
    token = "abc123"
    hash1 = security.hash_token(token)
    hash2 = security.hash_token(token)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 en hex = 64 chars


def test_given_short_secret_key_then_settings_validation_fails():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/app",
            TEST_DATABASE_URL="postgresql://user:pass@localhost:5432/app_test",
            SECRET_KEY=SecretStr("short"),
            LLM_API_KEY=SecretStr("test-api-key"),
            LLM_BASE_URL=HttpUrl("https://api.openai.com/v1"),
            LLM_MODEL="gpt-4o-mini",
        )
