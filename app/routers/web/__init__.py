"""Router compuesto de páginas web: login, dashboard y logs de auditoría."""

from fastapi import APIRouter

from app.routers.web.audit_logs import router as audit_logs_router
from app.routers.web.dashboard import router as dashboard_router
from app.routers.web.login import router as login_router

router = APIRouter()
router.include_router(login_router)
router.include_router(dashboard_router)
router.include_router(audit_logs_router)
