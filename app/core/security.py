from argon2 import PasswordHasher
from zxcvbn import zxcvbn
import re
password_hasher = PasswordHasher()


def hash_credential(credential: str) -> str:
    return password_hasher.hash(credential)


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
