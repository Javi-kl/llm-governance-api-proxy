import logging

from sqlalchemy.orm import Session
from app.repositories import audit_logs


logger = logging.getLogger("scheduler_service")


def cleanup_old_audit_logs(db: Session, retention_days: int = 90) -> int:
    deleted = audit_logs.delete_older_than(db, days=retention_days)
    logger.info(
        "Limpieza de audit logs completada: %s registros eliminados",
        deleted,
    )
    return deleted
