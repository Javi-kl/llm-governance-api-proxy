"""Excepciones de dominio — el lenguaje del negocio, no de HTTP."""


class DomainError(Exception):
    """Base para todas las excepciones del dominio."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class UserAlreadyExistsError(DomainError):
    """Se intentó crear un usuario con un username que ya existe."""

    def __init__(self, username: str) -> None:
        self.username = username
        super().__init__(f"El username '{username}' ya está registrado")

class UserNotFoundError(DomainError):
    """Se buscó un usuario que no existe."""

    def __init__(self, username: str) -> None:
        self.username = username
        super().__init__(f"Usuario '{username}' no encontrado")


class InvalidCredentialsError(DomainError):
    """Las credenciales proporcionadas no son válidas."""

    def __init__(self) -> None:
        super().__init__("Credenciales inválidas")


class WeakPasswordError(DomainError):
    """La contraseña no cumple la política de seguridad."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Contraseña débil: {reason}")
