"""Schemas para el envelope de error RF-8."""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str
    type: str | None = None


class ErrorEnvelope(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None
