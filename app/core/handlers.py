"""Traduce excepciones de dominio y errores de Pydantic
a respuestas HTTP con el envelope de RF-8 y OpenAI."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

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
    ModelNotFoundError,
)
from app.core.error_response import _error_response_for
from app.schemas.error import ErrorDetail

logger = logging.getLogger("error_handlers")


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(InvalidCredentialsError)
    async def invalid_credentials_handler(
        request: Request, exc: InvalidCredentialsError
    ):
        return _error_response_for(
            request,
            401,
            message="Credenciales no válidas",
            code="UNAUTHORIZED",
            openai_type="authentication_error",
        )

    @app.exception_handler(PermissionDeniedError)
    async def permission_denied_handler(request: Request, exc: PermissionDeniedError):
        return _error_response_for(
            request,
            403,
            message="No tienes permiso para hacer eso",
            code="FORBIDDEN",
            openai_type="permission_error",
        )

    @app.exception_handler(UserNotFoundError)
    async def user_not_found_handler(request: Request, exc: UserNotFoundError):
        return _error_response_for(
            request,
            404,
            message="Usuario no encontrado",
            code="USER_NOT_FOUND",
            openai_type="not_found_error",
        )

    @app.exception_handler(CannotModifyAdminError)
    async def cannot_modify_admin_handler(
        request: Request, exc: CannotModifyAdminError
    ):
        return _error_response_for(
            request,
            422,
            message="El administrador no puede ser modificado",
            code="ADMIN_NOT_MANAGEABLE",
            openai_type="invalid_request_error",
        )

    @app.exception_handler(InactiveUserError)
    async def inactive_user_handler(request: Request, exc: InactiveUserError):
        return _error_response_for(
            request,
            422,
            message="El usuario está desactivado",
            code="USER_INACTIVE",
            openai_type="invalid_request_error",
        )

    @app.exception_handler(PasswordReuseError)
    async def password_reuse_handler(request: Request, exc: PasswordReuseError):
        return _error_response_for(
            request,
            400,
            message="La nueva contraseña no puede ser igual a la actual",
            code="PASSWORD_REUSE",
            openai_type="invalid_request_error",
        )

    @app.exception_handler(UserAlreadyExistsError)
    async def user_already_exists_handler(
        request: Request, exc: UserAlreadyExistsError
    ):
        return _error_response_for(
            request,
            409,
            message="Este nombre de usuario ya está registrado",
            code="USER_ALREADY_EXISTS",
            openai_type="invalid_request_error",
        )

    @app.exception_handler(ProviderTimeoutError)
    async def provider_timeout_handler(request: Request, exc: ProviderTimeoutError):
        return _error_response_for(
            request,
            504,
            message="El proveedor externo no respondió a tiempo",
            code="UPSTREAM_TIMEOUT",
            openai_type="api_error",
        )

    @app.exception_handler(ProviderError)
    async def provider_error_handler(request: Request, exc: ProviderError):
        return _error_response_for(
            request,
            502,
            message="Error del proveedor externo",
            code="UPSTREAM_ERROR",
            openai_type="api_error",
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        list_of_errors = exc.errors()
        details = [
            ErrorDetail(
                field=str(error.get("loc", ())[-1]) if error.get("loc") else "body",
                message=error.get("msg", ""),
                type=error.get("type", ""),
            )
            for error in list_of_errors
        ]
        error = list_of_errors[0]
        param = error["loc"][1] if len(error["loc"]) >= 2 else None

        return _error_response_for(
            request,
            422,
            message="La solicitud contiene datos inválidos",
            code="VALIDATION_ERROR",
            openai_type="invalid_request_error",
            param=param,
            details=details,
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("Error interno no manejado: %s", exc)

        return _error_response_for(
            request,
            500,
            message="Error interno del servidor",
            code="INTERNAL_ERROR",
            openai_type="api_error",
        )

    @app.exception_handler(ModelNotFoundError)
    async def model_not_found_handler(request: Request, exc: ModelNotFoundError):
        return _error_response_for(
            request,
            404,
            message="Modelo no disponible",
            code="MODEL_NOT_FOUND",
            openai_type="not_found_error",
        )
