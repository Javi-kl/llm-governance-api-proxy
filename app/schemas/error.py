"""Schemas para el envelope de error RF-8."""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Un error puntual de validación (campo, mensaje, tipo)."""

    field: str | None = None
    message: str
    type: str | None = None


class ErrorEnvelope(BaseModel):
    """Contenido del campo 'error': código, mensaje y detalles opcionales."""

    code: str
    message: str
    details: list[ErrorDetail] | None = None
