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

    def __init__(self, identifier: str | int) -> None:
        self.identifier = identifier
        super().__init__(f"Usuario '{identifier}' no encontrado")


class InvalidCredentialsError(DomainError):
    """Las credenciales proporcionadas no son válidas."""

    def __init__(self) -> None:
        super().__init__("Credenciales inválidas")


class WeakPasswordError(DomainError):
    """La contraseña no cumple la política de seguridad."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Contraseña débil: {reason}")


class PasswordReuseError(DomainError):
    """La nueva contraseña no puede ser igual a la actual."""

    def __init__(self) -> None:
        super().__init__("La nueva contraseña no puede ser igual a la actual")


class PermissionDeniedError(DomainError):
    """Permiso denegado."""

    def __init__(self) -> None:
        super().__init__("No tienes permiso para hacer eso.")

class CannotModifyAdminError(DomainError):
    """Un admin no se puede modificar"""
    
    def __init__(self) -> None:
        super().__init__("El administrador no puede ser modificado.")

class InactiveUserError(DomainError):
    "Usuario inactivo"
    
    def __init__(self) -> None:
        super().__init__("El usuario está desactivado.")


class ProviderTimeoutError(DomainError):
    """El proveedor LLM externo no respondió a tiempo."""

    def __init__(self) -> None:
        super().__init__("El proveedor externo no respondió a tiempo")


class ProviderError(DomainError):
    """El proveedor LLM externo devolvió un error o no se pudo conectar."""

    def __init__(self, status_code: int | None = None) -> None:
        self.status_code = status_code
        detail = f" (HTTP {status_code})" if status_code else ""
        super().__init__(f"Error del proveedor externo{detail}")