from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogFilter(BaseModel):
    """Filtros para GET /admin/logs (query params)."""

    action: str | None = None  # "allow" | "mask" | "block" | "error"
    user_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = 1
    page_size: int = 50


class AuditLogResponse(BaseModel):
    """Un registro de auditoría individual."""

    request_id: str
    timestamp: datetime
    user_id: int
    provider: str
    model: str
    action: str
    detected_categories: list[str]
    latency_ms: int
    status: str
    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    """Lista paginada de registros de auditoría."""

    items: list[AuditLogResponse]
    total: int


class ComplianceReport(BaseModel):
    """Informe de cumplimiento (RF-19)."""

    total_requests: int
    by_action: dict[str, int]  # {"allow": 10, "mask": 5, "block": 2, "error": 1}
    top_categories: list[str]  # Top 5 categorías más detectadas
    last_cleanup: str | None  # Fecha de última limpieza de retención
