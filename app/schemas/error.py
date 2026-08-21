"""Schemas para el envelope de error de RF-8 y OpenAI."""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str
    type: str | None = None


class ErrorEnvelope(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None


class OpenAIErrorBody(BaseModel):
    message: str
    type: str
    param: str | None = None
    code: str | None = None
