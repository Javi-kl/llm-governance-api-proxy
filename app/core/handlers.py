from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    CannotModifyAdminError,
    InactiveUserError,
    InvalidCredentialsError,
    PasswordReuseError,
    PermissionDeniedError,
    UserAlreadyExistsError,
    UserNotFoundError,
)


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[dict] | None = None,
) -> JSONResponse:
    """Construye una JSONResponse con el envelope de error RF-8."""
    body: dict = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(InvalidCredentialsError)
    async def invalid_credentials_handler(
        request: Request, exc: InvalidCredentialsError
    ):
        return _error_response(401, "UNAUTHORIZED", "Credenciales no válidas")

    @app.exception_handler(PermissionDeniedError)
    async def permission_denied_handler(
        request: Request, exc: PermissionDeniedError
    ):
        return _error_response(403, "FORBIDDEN", "No tienes permiso para hacer eso")

    @app.exception_handler(UserNotFoundError)
    async def user_not_found_handler(
        request: Request, exc: UserNotFoundError
    ):
        return _error_response(404, "USER_NOT_FOUND", "Usuario no encontrado")

    @app.exception_handler(CannotModifyAdminError)
    async def cannot_modify_admin_handler(
        request: Request, exc: CannotModifyAdminError
    ):
        return _error_response(
            422, "ADMIN_NOT_MANAGEABLE",
            "El administrador no puede ser modificado."
        )

    @app.exception_handler(InactiveUserError)
    async def inactive_user_handler(
        request: Request, exc: InactiveUserError
    ):
        return _error_response(
            422, "USER_INACTIVE", "El usuario está desactivado."
        )

    @app.exception_handler(PasswordReuseError)
    async def password_reuse_handler(
        request: Request, exc: PasswordReuseError
    ):
        return _error_response(
            400, "PASSWORD_REUSE",
            "La nueva contraseña no puede ser igual a la actual"
        )

    @app.exception_handler(UserAlreadyExistsError)
    async def user_already_exists_handler(
        request: Request, exc: UserAlreadyExistsError
    ):
        return _error_response(
            409, "USER_ALREADY_EXISTS",
            "Este username ya está registrado"
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ):
        details: list[dict] = []
        for error in exc.errors():
            loc: tuple = error.get("loc", ())
            field: str = str(loc[-1]) if loc else "body"
            details.append({
                "field": field,
                "message": error.get("msg", ""),
                "type": error.get("type", ""),
            })
        return _error_response(
            422,
            "VALIDATION_ERROR",
            "La solicitud contiene datos inválidos",
            details=details,
        )
