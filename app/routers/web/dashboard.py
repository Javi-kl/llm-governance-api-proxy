"""Ruta web del dashboard de administración.

Protegido con require_admin: solo usuarios con rol admin pueden acceder.
Usuario normal → 403, sin sesión → 401.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.db.models.user import User
from app.dependencies.auth_dep import require_admin
from app.routers.web.common import _render_template

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
) -> HTMLResponse:
    """
    Usuario normal → 403, sin sesión → 401 vía los handlers de excepción.
    """
    return _render_template(
        request,
        "dashboard.html",
        user=current_user,
    )
