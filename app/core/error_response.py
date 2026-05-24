"""Helper compartido para construir respuestas de error con el envelope RF-8."""

from fastapi.responses import JSONResponse

from app.schemas.error import ErrorEnvelope


def error_response(status_code: int, envelope: ErrorEnvelope) -> JSONResponse:
    """Construye una JSONResponse con el envelope de error estándar."""
    body = {"error": envelope.model_dump()}
    return JSONResponse(status_code=status_code, content=body)
