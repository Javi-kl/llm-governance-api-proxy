import logging
from contextlib import contextmanager
from datetime import timedelta

from app.core import scheduler as scheduler_module


def test_given_start_scheduler_then_registers_retention_job():
    """Registra el job de retención de audit logs con ejecución cada 24 horas."""
    scheduler = scheduler_module.start_scheduler()

    try:
        job = scheduler.get_job("audit_log_retention_cleanup")

        assert job is not None
        assert job.func is scheduler_module.run_audit_log_retention_cleanup
        assert job.trigger.interval == timedelta(hours=24)
    finally:
        scheduler_module.stop_scheduler(scheduler)


def test_given_retention_job_runs_then_opens_db_and_calls_cleanup(monkeypatch):
    """Abre una sesión de base de datos y delega la limpieza al servicio."""
    fake_db = object()
    called_with: list[object] = []

    @contextmanager
    def fake_get_db_context():
        yield fake_db

    def fake_cleanup_old_audit_logs(db):
        called_with.append(db)

    monkeypatch.setattr(scheduler_module, "get_db_context", fake_get_db_context)
    monkeypatch.setattr(
        scheduler_module,
        "cleanup_old_audit_logs",
        fake_cleanup_old_audit_logs,
    )

    scheduler_module.run_audit_log_retention_cleanup()

    assert called_with == [fake_db]


def test_given_cleanup_fails_then_job_logs_exception(monkeypatch, caplog):
    """Registra un error técnico si falla la limpieza programada."""
    fake_db = object()

    @contextmanager
    def fake_get_db_context():
        yield fake_db

    def fake_cleanup_old_audit_logs(db):
        raise RuntimeError("fallo de limpieza")

    monkeypatch.setattr(scheduler_module, "get_db_context", fake_get_db_context)
    monkeypatch.setattr(
        scheduler_module,
        "cleanup_old_audit_logs",
        fake_cleanup_old_audit_logs,
    )

    with caplog.at_level(logging.ERROR, logger="scheduler_core"):
        scheduler_module.run_audit_log_retention_cleanup()

    assert "Error ejecutando limpieza de audit logs" in caplog.text
