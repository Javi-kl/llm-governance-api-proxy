from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog
from app.db.models.user import User
from app.services.audit import register_log
from app.services.scheduler import cleanup_old_audit_logs


def _create_audit_log_with_age(
    db: Session,
    user: User,
    *,
    request_id: str,
    age_days: int,
) -> AuditLog:
    """Crea un audit log y ajusta su fecha para probar la retención."""
    register_log(
        request_id=request_id,
        user_id=user.id,
        provider="openai",
        model="gpt-4o-mini",
        action="allow",
        detected_categories=[],
        latency_ms=100,
        status="success",
        db=db,
    )
    log = db.query(AuditLog).filter_by(request_id=request_id).one()
    log.timestamp = datetime.utcnow() - timedelta(days=age_days)
    db.flush()
    return log


def test_given_old_audit_log_then_cleanup_deletes_it(
    db_session: Session,
    regular_user: User,
):
    """Elimina los audit logs más antiguos que la ventana de retención."""

    request_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    _create_audit_log_with_age(
        db_session,
        regular_user,
        request_id=request_id,
        age_days=91,
    )

    deleted = cleanup_old_audit_logs(db_session, retention_days=90)

    remaining = (
        db_session.query(AuditLog).filter_by(request_id=request_id).one_or_none()
    )
    assert deleted == 1
    assert remaining is None


def test_given_recent_audit_log_then_cleanup_keeps_it(
    db_session: Session,
    regular_user: User,
):
    """Conserva los audit logs que todavía están dentro de la ventana de retención."""

    request_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    _create_audit_log_with_age(
        db_session,
        regular_user,
        request_id=request_id,
        age_days=89,
    )

    deleted = cleanup_old_audit_logs(db_session, retention_days=90)

    remaining = (
        db_session.query(AuditLog).filter_by(request_id=request_id).one_or_none()
    )
    assert deleted == 0
    assert remaining is not None


def test_given_no_audit_logs_then_cleanup_returns_zero(db_session: Session):
    """Devuelve 0 cuando no hay audit logs que limpiar."""
    deleted = cleanup_old_audit_logs(db_session, retention_days=90)

    assert deleted == 0
