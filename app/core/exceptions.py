"""Excepciones de dominio — el lenguaje del negocio, no de HTTP."""


class DomainError(Exception):
    """Base para todas las excepciones del dominio."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class UserAlreadyExistsError(DomainError):
    def __init__(self, username: str) -> None:
        self.username = username
        super().__init__(f"El username '{username}' ya está registrado")


class UserNotFoundError(DomainError):
    def __init__(self, identifier: str | int) -> None:
        self.identifier = identifier
        super().__init__(f"Usuario '{identifier}' no encontrado")


class InvalidCredentialsError(DomainError):
    def __init__(self) -> None:
        super().__init__("Credenciales inválidas")


class WeakPasswordError(DomainError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Contraseña débil: {reason}")


class PasswordReuseError(DomainError):
    def __init__(self) -> None:
        super().__init__("La nueva contraseña no puede ser igual a la actual")


class PermissionDeniedError(DomainError):
    def __init__(self) -> None:
        super().__init__("No tienes permiso para hacer eso.")


class CannotModifyAdminError(DomainError):
    def __init__(self) -> None:
        super().__init__("El administrador no puede ser modificado.")


class InactiveUserError(DomainError):
    def __init__(self) -> None:
        super().__init__("El usuario está desactivado.")


class ProviderTimeoutError(DomainError):
    def __init__(self) -> None:
        super().__init__("El proveedor externo no respondió a tiempo")


class ProviderError(DomainError):
    def __init__(self, status_code: int | None = None) -> None:
        self.status_code = status_code
        detail = f" (HTTP {status_code})" if status_code else ""
        super().__init__(f"Error del proveedor externo{detail}")
