"""Servicio de auditoría del proxy.

Registra y consulta metadatos de solicitudes sin almacenar prompts
ni respuestas del proveedor LLM.
Genera informes agregados de cumplimiento.
"""

from collections import Counter
from datetime import datetime

from sqlalchemy.orm import Session

from app.repositories import audit_logs
from app.schemas.admin import (
    AuditLogFilter,
    AuditLogListResponse,
    AuditLogResponse,
    ComplianceReport,
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


def generate_report(
    db: Session,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> ComplianceReport:
    total = audit_logs.count_in_range(db, date_from, date_to)
    by_action = {
        "allow": 0,
        "mask": 0,
        "block": 0,
        "error": 0,
    }
    by_action.update(audit_logs.count_by_action(db, date_from, date_to))

    all_categories = audit_logs.get_all_detected_categories(db, date_from, date_to)
    counter: Counter[str] = Counter()
    for entry in all_categories:
        counter.update(entry)
    top_5 = [cat for cat, _ in counter.most_common(5)]

    return ComplianceReport(
        total_requests=total,
        by_action=by_action,
        top_categories=top_5,
        last_cleanup=None,
    )
