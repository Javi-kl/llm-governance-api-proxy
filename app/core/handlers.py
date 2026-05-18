from fastapi import FastAPI, Request
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


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidCredentialsError)
    async def invalid_credentials_handler(request: Request, exc: InvalidCredentialsError):# type: ignore[unused-function]
        return JSONResponse(
            status_code=401,
            content={"detail": "Credenciales no válidas"},
        )

    @app.exception_handler(PermissionDeniedError)
    async def permission_denied_handler(request: Request, exc: PermissionDeniedError):# type: ignore[unused-function]
        return JSONResponse(
            status_code=403,
            content={"detail": "No tienes permiso para hacer eso"},
        )

    @app.exception_handler(UserNotFoundError)
    async def user_not_found_handler(request: Request, exc: UserNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"detail": "Usuario no encontrado"},
        )

    @app.exception_handler(CannotModifyAdminError)
    async def cannot_modify_admin_handler(request: Request, exc: CannotModifyAdminError):
        return JSONResponse(
            status_code=422,
            content={"detail": "El administrador no puede ser modificado."},
        )

    @app.exception_handler(InactiveUserError)
    async def inactive_user_handler(request: Request, exc: InactiveUserError):
        return JSONResponse(
            status_code=422,
            content={"detail": "El usuario esta desactivado."},
        )

    @app.exception_handler(PasswordReuseError)
    async def password_reuse_handler(request: Request, exc: PasswordReuseError):
        return JSONResponse(
            status_code=400,
            content={"detail": "La nueva contraseña no puede ser igual a la actual"},
        )

    @app.exception_handler(UserAlreadyExistsError)
    async def user_already_exists_handler(request: Request, exc: UserAlreadyExistsError):
        return JSONResponse(
            status_code=409,
            content={"detail": "Este username ya está registrado"},
        )