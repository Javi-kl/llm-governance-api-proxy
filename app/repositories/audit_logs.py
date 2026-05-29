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
    """Persiste un registro de auditoría. Sigue el patrón de users.create()."""
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
    """
    Lista logs de auditoría con filtros opcionales y paginación.
    Sigue el patrón de users.get_all_normal_users():
    query base → .where() condicionales → subquery para count → offset/limit.
    Orden: timestamp descendente (más recientes primero).
    """
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


def count_in_range(
    db: Session,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> int:
    """Cuenta el total de registros en el rango de fechas."""
    base = select(func.count()).select_from(AuditLog)
    if date_from is not None:
        base = base.where(AuditLog.timestamp >= date_from)
    if date_to is not None:
        base = base.where(AuditLog.timestamp <= date_to)
    return db.execute(base).scalar_one()


def count_by_action(
    db: Session,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, int]:
    """Cuenta registros agrupados por acción en el rango de fechas."""
    stmt = select(
        AuditLog.action, func.count().label("total")
    ).group_by(AuditLog.action)
    if date_from is not None:
        stmt = stmt.where(AuditLog.timestamp >= date_from)
    if date_to is not None:
        stmt = stmt.where(AuditLog.timestamp <= date_to)
    rows = db.execute(stmt).all()
    return {row.action: row.total for row in rows}


def get_all_detected_categories(
    db: Session,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[list[str]]:
    """Obtiene todas las listas de categorías detectadas en el rango."""
    stmt = select(AuditLog.detected_categories)
    if date_from is not None:
        stmt = stmt.where(AuditLog.timestamp >= date_from)
    if date_to is not None:
        stmt = stmt.where(AuditLog.timestamp <= date_to)
    return [row.detected_categories for row in db.execute(stmt).all()]
