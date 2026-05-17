import jwt

import pytest
from datetime import timedelta

from app.core import config, security
from app.core.enums import UserRole


# ── create_access_token ──────────────────────────────────


def test_create_access_token_given_valid_subject_then_returns_decodable_jwt():
    token = security.create_access_token(42, UserRole.USER)

    payload = jwt.decode(
        token,
        config.get_settings().SECRET_KEY.get_secret_value(),
        algorithms=[config.get_settings().ALGORITHM],
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
        algorithms=[config.get_settings().ALGORITHM],
        options={"verify_exp": False},
    )

    delta = payload["exp"] - payload["iat"]
    assert delta == pytest.approx(300, abs=2)


def test_create_access_token_given_no_expiry_then_uses_default_60_minutes():
    token = security.create_access_token(42, UserRole.USER)

    payload = jwt.decode(
        token,
        config.get_settings().SECRET_KEY.get_secret_value(),
        algorithms=[config.get_settings().ALGORITHM],
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
