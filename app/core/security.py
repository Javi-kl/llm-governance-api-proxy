from argon2 import PasswordHasher
from zxcvbn import zxcvbn

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")
    result = zxcvbn(password)
    if result["score"] < 2:
        raise ValueError("La contraseña no es lo suficientemente segura")
    return password
