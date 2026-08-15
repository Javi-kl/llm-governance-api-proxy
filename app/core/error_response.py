"""Helper compartido para construir respuestas de error con el envelope RF-8 y OpenAI."""

from fastapi.responses import JSONResponse

from app.schemas.error import ErrorEnvelope, OpenAIErrorBody


def error_response(status_code: int, envelope: ErrorEnvelope) -> JSONResponse:
    body = {"error": envelope.model_dump()}
    return JSONResponse(status_code=status_code, content=body)


def openai_error_response(status_code: int, envelope: OpenAIErrorBody) -> JSONResponse:
    body = {"error": envelope.model_dump()}
    return JSONResponse(status_code=status_code, content=body)
