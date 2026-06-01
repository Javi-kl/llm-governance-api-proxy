from sqlalchemy.orm import Session

from app.db.models.user import User
from app.schemas.admin import AuditLogFilter, AuditLogResponse
from app.services.audit import generate_report, list_logs, register_log


# ── Helpers ────────────────────────────────────────────────

_contador = 0


def _create_log(
    db: Session,
    user: User,
    action: str = "allow",
    categories: list[str] | None = None,
    request_id: str | None = None,
) -> AuditLogResponse:
    """Atajo para crear un registro de auditoría en tests."""
    global _contador
    _contador += 1
    rid = request_id or f"req-{_contador}"
    cats = categories if categories is not None else []
    return register_log(
        request_id=rid,
        user_id=user.id,
        provider="openai",
        model="gpt-4o-mini",
        action=action,
        detected_categories=cats,
        latency_ms=100,
        status="success",
        db=db,
    )


# ── Ciclo 1: Registrar log ────────────────────────────────


def test_register_log(db_session: Session, regular_user: User):
    result = _create_log(db_session, regular_user, request_id="abc-123")

    assert isinstance(result, AuditLogResponse)
    assert result.request_id == "abc-123"
    assert result.user_id == regular_user.id
    assert result.action == "allow"


# ── Ciclo 2: Listar logs ──────────────────────────────────


def test_list_logs_filter_by_action(db_session: Session, regular_user: User):
    _create_log(db_session, regular_user, action="allow")
    _create_log(db_session, regular_user, action="allow")
    _create_log(db_session, regular_user, action="block", request_id="req-block")

    filter_ = AuditLogFilter(action="block")
    result = list_logs(filter_, db_session)

    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].action == "block"


def test_list_logs_pagination(db_session: Session, regular_user: User):
    for i in range(5):
        _create_log(db_session, regular_user, request_id=f"req-{i}")

    filter_ = AuditLogFilter(page=2, page_size=2)
    result = list_logs(filter_, db_session)

    assert result.total == 5
    assert len(result.items) == 2


def test_list_logs_without_results(db_session: Session, regular_user: User):
    _create_log(db_session, regular_user, action="allow")

    filter_ = AuditLogFilter(action="block")
    result = list_logs(filter_, db_session)

    assert result.total == 0
    assert result.items == []


# ── Ciclo 3: Generar informe ───────────────────────────────


def test_generate_report_with_data(db_session: Session, regular_user: User):
    _create_log(db_session, regular_user, action="allow")
    _create_log(db_session, regular_user, action="allow")
    _create_log(db_session, regular_user, action="mask", categories=["identificacion"])
    _create_log(db_session, regular_user, action="block", categories=["financiero"])

    report = generate_report(db_session)

    assert report.total_requests == 4
    assert report.by_action == {
        "allow": 2,
        "mask": 1,
        "block": 1,
        "error": 0,
    }
    assert "financiero" in report.top_categories
    assert "identificacion" in report.top_categories


def test_generate_report_without_data(db_session: Session, regular_user: User):
    report = generate_report(db_session)

    assert report.total_requests == 0
    assert report.by_action == {
        "allow": 0,
        "mask": 0,
        "block": 0,
        "error": 0,
    }
    assert report.top_categories == []
    assert report.last_cleanup is None


def test_generate_report_with_range(db_session: Session, regular_user: User):
    _create_log(db_session, regular_user, action="allow")
    _create_log(db_session, regular_user, action="block", categories=["financiero"])

    from datetime import datetime, timedelta

    future = datetime.utcnow() + timedelta(days=1)
    report = generate_report(db_session, date_to=future - timedelta(hours=1))

    # Solo los logs insertados con server_default=now() entran en el rango
    assert report.total_requests >= 2
