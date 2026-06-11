"""Consultas de persistencia para audit_logs.

Centraliza inserción, filtrado y limpieza de retención sobre los
metadatos de auditoría del proxy. No debe guardar prompts ni respuestas
del proveedor LLM.
"""

from datetime import datetime, timedelta
from typing import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog


def create(
    request_id: str,
    user_id: int,
    provider: str,
    model: str,
    action: str,
    detected_categories: list[str],
    latency_ms: int,
    status: str,
    db: Session,
) -> AuditLog:

    log = AuditLog(
        request_id=request_id,
        user_id=user_id,
        provider=provider,
        model=model,
        action=action,
        detected_categories=detected_categories,
        latency_ms=latency_ms,
        status=status,
    )
    db.add(log)
    db.flush()
    return log


def list_logs(
    db: Session,
    action: str | None = None,
    user_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[Sequence[AuditLog], int]:

    base_query = select(AuditLog)
    if action is not None:
        base_query = base_query.where(AuditLog.action == action)
    if user_id is not None:
        base_query = base_query.where(AuditLog.user_id == user_id)
    if date_from is not None:
        base_query = base_query.where(AuditLog.timestamp >= date_from)
    if date_to is not None:
        base_query = base_query.where(AuditLog.timestamp <= date_to)
    # Subquery para count total con los mismos filtros
    total = db.execute(
        select(func.count()).select_from(base_query.subquery())
    ).scalar_one()
    items = (
        db.execute(
            base_query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
        )
        .scalars()
        .all()
    )
    return items, total


def delete_older_than(db: Session, days: int = 90) -> int:
    """
    Elimina registros con más de `days` días de antigüedad.
    Retorna el número de filas eliminadas.
    Usado por el scheduler de retención (RAL-2, ADR-9).
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    count = db.execute(
        select(func.count()).select_from(
            select(AuditLog.id).where(AuditLog.timestamp < cutoff).subquery()
        )
    ).scalar_one()
    if count > 0:
        db.execute(delete(AuditLog).where(AuditLog.timestamp < cutoff))
        db.flush()
    return count
