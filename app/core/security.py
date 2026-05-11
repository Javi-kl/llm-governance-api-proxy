import re
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from zxcvbn import zxcvbn

from app.core.config import get_settings
from app.core.enums import UserRole

password_hasher = PasswordHasher()
settings = get_settings()


def create_access_token(
    subject: str, role: UserRole, expires_delta: timedelta | None = None
) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "iat": now,
        "role": role,
        "exp": now + expires_delta,
    }

    return jwt.encode(
        payload, settings.SECRET_KEY.get_secret_value(), algorithm=settings.ALGORITHM
    )


def hash_credential(credential: str) -> str:
    return password_hasher.hash(credential)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return password_hasher.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except InvalidHashError:
        return False


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")
    result = zxcvbn(password)
    if result["score"] < 2:
        raise ValueError("La contraseña no es lo suficientemente segura")
    return password


def validate_pin(pin: str) -> str:
    if not re.match(r"^\d{5,6}$", pin):
        raise ValueError("El PIN debe contener entre 5 y 6 dígitos")
    return pin
