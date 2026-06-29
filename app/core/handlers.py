"""Traduce excepciones de dominio y errores de Pydantic
a respuestas HTTP con el envelope RF-8."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from app.core.error_response import error_response
from app.core.exceptions import (
    CannotModifyAdminError,
    InactiveUserError,
    InvalidCredentialsError,
    PasswordReuseError,
    PermissionDeniedError,
    ProviderError,
    ProviderTimeoutError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.schemas.error import ErrorDetail, ErrorEnvelope

logger = logging.getLogger("error_handlers")


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(InvalidCredentialsError)
    async def invalid_credentials_handler(
        request: Request, exc: InvalidCredentialsError
    ):
        return error_response(
            401,
            ErrorEnvelope(code="UNAUTHORIZED", message="Credenciales no válidas"),
        )

    @app.exception_handler(PermissionDeniedError)
    async def permission_denied_handler(request: Request, exc: PermissionDeniedError):
        return error_response(
            403,
            ErrorEnvelope(code="FORBIDDEN", message="No tienes permiso para hacer eso"),
        )

    @app.exception_handler(UserNotFoundError)
    async def user_not_found_handler(request: Request, exc: UserNotFoundError):
        return error_response(
            404,
            ErrorEnvelope(code="USER_NOT_FOUND", message="Usuario no encontrado"),
        )

    @app.exception_handler(CannotModifyAdminError)
    async def cannot_modify_admin_handler(
        request: Request, exc: CannotModifyAdminError
    ):
        return error_response(
            422,
            ErrorEnvelope(
                code="ADMIN_NOT_MANAGEABLE",
                message="El administrador no puede ser modificado.",
            ),
        )

    @app.exception_handler(InactiveUserError)
    async def inactive_user_handler(request: Request, exc: InactiveUserError):
        return error_response(
            422,
            ErrorEnvelope(code="USER_INACTIVE", message="El usuario está desactivado."),
        )

    @app.exception_handler(PasswordReuseError)
    async def password_reuse_handler(request: Request, exc: PasswordReuseError):
        return error_response(
            400,
            ErrorEnvelope(
                code="PASSWORD_REUSE",
                message="La nueva contraseña no puede ser igual a la actual",
            ),
        )

    @app.exception_handler(UserAlreadyExistsError)
    async def user_already_exists_handler(
        request: Request, exc: UserAlreadyExistsError
    ):
        return error_response(
            409,
            ErrorEnvelope(
                code="USER_ALREADY_EXISTS",
                message="Este username ya está registrado",
            ),
        )

    @app.exception_handler(ProviderTimeoutError)
    async def provider_timeout_handler(request: Request, exc: ProviderTimeoutError):
        return error_response(
            504,
            ErrorEnvelope(
                code="UPSTREAM_TIMEOUT",
                message="El proveedor externo no respondió a tiempo",
            ),
        )

    @app.exception_handler(ProviderError)
    async def provider_error_handler(request: Request, exc: ProviderError):
        return error_response(
            502,
            ErrorEnvelope(
                code="UPSTREAM_ERROR",
                message="Error del proveedor externo",
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        details = [
            ErrorDetail(
                field=str(error.get("loc", ())[-1]) if error.get("loc") else "body",
                message=error.get("msg", ""),
                type=error.get("type", ""),
            )
            for error in exc.errors()
        ]
        return error_response(
            422,
            ErrorEnvelope(
                code="VALIDATION_ERROR",
                message="La solicitud contiene datos inválidos",
                details=details,
            ),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("Error interno no manejado: %s", exc)
        return error_response(
            500,
            ErrorEnvelope(code="INTERNAL_ERROR", message="Error interno del servidor"),
        )
