"""
Registra y consulta metadatos de solicitudes sin almacenar prompts
ni respuestas.
"""

from sqlalchemy.orm import Session

from app.repositories import audit_logs
from app.schemas.admin import (
    AuditLogFilter,
    AuditLogListResponse,
    AuditLogResponse,
)


def register_log(
    request_id: str,
    user_id: int,
    provider: str,
    model: str,
    action: str,
    detected_categories: list[str],
    latency_ms: int,
    status: str,
    db: Session,
) -> AuditLogResponse:
    log = audit_logs.create(
        request_id=request_id,
        user_id=user_id,
        provider=provider,
        model=model,
        action=action,
        detected_categories=detected_categories,
        latency_ms=latency_ms,
        status=status,
        db=db,
    )
    return AuditLogResponse.model_validate(log)


def list_logs(filter_: AuditLogFilter, db: Session) -> AuditLogListResponse:
    offset = (filter_.page - 1) * filter_.page_size
    items, total = audit_logs.list_logs(
        db=db,
        action=filter_.action,
        user_id=filter_.user_id,
        date_from=filter_.date_from,
        date_to=filter_.date_to,
        offset=offset,
        limit=filter_.page_size,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(i) for i in items],
        total=total,
    )
