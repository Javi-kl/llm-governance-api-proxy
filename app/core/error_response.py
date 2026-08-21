"""Helper compartido para construir respuestas de error con el envelope RF-8 y OpenAI."""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.schemas.error import ErrorDetail, ErrorEnvelope, OpenAIErrorBody


def _error_response_for(
    request: Request,
    status_code: int,
    message: str,
    openai_type: str,
    code: str,
    param: str | None = None,
    details: list[ErrorDetail] | None = None,
):
    if request.url.path.startswith("/v1/"):
        return openai_error_response(
            status_code,
            OpenAIErrorBody(
                message=message,
                type=openai_type,
                param=param,
            ),
        )
    return error_response(
        status_code, ErrorEnvelope(code=code, message=message, details=details)
    )


def error_response(status_code: int, envelope: ErrorEnvelope) -> JSONResponse:
    body = {"error": envelope.model_dump()}
    return JSONResponse(status_code=status_code, content=body)


def openai_error_response(status_code: int, envelope: OpenAIErrorBody) -> JSONResponse:
    body = {"error": envelope.model_dump()}
    return JSONResponse(status_code=status_code, content=body)
