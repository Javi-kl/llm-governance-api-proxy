import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.services.scheduler import cleanup_old_audit_logs
from app.db.database import get_db_context

logger = logging.getLogger("scheduler_core")


def run_audit_log_retention_cleanup() -> None:
    try:
        with get_db_context() as db:
            cleanup_old_audit_logs(db)
    except Exception:
        logger.exception("Error ejecutando limpieza de audit logs")


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_audit_log_retention_cleanup,
        trigger="interval",
        hours=24,
        id="audit_log_retention_cleanup",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler


def stop_scheduler(scheduler: BackgroundScheduler) -> None:
    scheduler.shutdown(wait=False)
