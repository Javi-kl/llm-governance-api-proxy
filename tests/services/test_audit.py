from sqlalchemy.orm import Session

from app.db.models.user import User
from app.schemas.admin import AuditLogFilter, AuditLogResponse
from app.services.audit import generar_informe, listar_logs, registrar_log


# ── Helpers ────────────────────────────────────────────────

_contador = 0


def _crear_log(
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
    return registrar_log(
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


def test_registrar_log(db_session: Session, regular_user: User):
    resultado = _crear_log(db_session, regular_user, request_id="abc-123")

    assert isinstance(resultado, AuditLogResponse)
    assert resultado.request_id == "abc-123"
    assert resultado.user_id == regular_user.id
    assert resultado.action == "allow"


# ── Ciclo 2: Listar logs ──────────────────────────────────


def test_listar_logs_filtra_por_action(db_session: Session, regular_user: User):
    _crear_log(db_session, regular_user, action="allow")
    _crear_log(db_session, regular_user, action="allow")
    _crear_log(db_session, regular_user, action="block", request_id="req-block")

    filtro = AuditLogFilter(action="block")
    resultado = listar_logs(filtro, db_session)

    assert resultado.total == 1
    assert len(resultado.items) == 1
    assert resultado.items[0].action == "block"


def test_listar_logs_paginacion(db_session: Session, regular_user: User):
    for i in range(5):
        _crear_log(db_session, regular_user, request_id=f"req-{i}")

    filtro = AuditLogFilter(page=2, page_size=2)
    resultado = listar_logs(filtro, db_session)

    assert resultado.total == 5
    assert len(resultado.items) == 2


def test_listar_logs_sin_resultados(db_session: Session, regular_user: User):
    _crear_log(db_session, regular_user, action="allow")

    filtro = AuditLogFilter(action="block")
    resultado = listar_logs(filtro, db_session)

    assert resultado.total == 0
    assert resultado.items == []


# ── Ciclo 3: Generar informe ───────────────────────────────


def test_generar_informe_con_datos(db_session: Session, regular_user: User):
    _crear_log(db_session, regular_user, action="allow")
    _crear_log(db_session, regular_user, action="allow")
    _crear_log(db_session, regular_user, action="mask", categories=["identificacion"])
    _crear_log(db_session, regular_user, action="block", categories=["financiero"])

    reporte = generar_informe(db_session)

    assert reporte.total_requests == 4
    assert reporte.by_action == {
        "allow": 2,
        "mask": 1,
        "block": 1,
        "error": 0,
    }
    assert "financiero" in reporte.top_categories
    assert "identificacion" in reporte.top_categories


def test_generar_informe_sin_datos(db_session: Session, regular_user: User):
    reporte = generar_informe(db_session)

    assert reporte.total_requests == 0
    assert reporte.by_action == {
        "allow": 0,
        "mask": 0,
        "block": 0,
        "error": 0,
    }
    assert reporte.top_categories == []
    assert reporte.last_cleanup is None


def test_generar_informe_con_rango(db_session: Session, regular_user: User):
    _crear_log(db_session, regular_user, action="allow")
    _crear_log(db_session, regular_user, action="block", categories=["financiero"])

    from datetime import datetime, timedelta

    futuro = datetime.utcnow() + timedelta(days=1)
    reporte = generar_informe(db_session, date_to=futuro - timedelta(hours=1))

    # Solo los logs insertados con server_default=now() entran en el rango
    assert reporte.total_requests >= 2
