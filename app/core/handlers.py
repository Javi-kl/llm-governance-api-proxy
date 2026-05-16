from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import CannotModifyAdminError, InactiveUserError, InvalidCredentialsError, PermissionDeniedError, UserNotFoundError


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