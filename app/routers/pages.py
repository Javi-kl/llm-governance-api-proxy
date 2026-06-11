"""Rutas de páginas web del proxy: raíz, login y dashboard.

El login web reutiliza auth_service.login() — la misma lógica que la API REST.
En vez de devolver JSON, responde con cookies + HX-Redirect (éxito)
o re-renderiza el formulario con error (fallo).

El dashboard está protegido con require_admin: solo usuarios con rol admin
pueden acceder. Usuario normal → 403, sin sesión → 401.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.core.cookies import set_auth_cookies
from app.core.enums import UserRole
from app.core.exceptions import InvalidCredentialsError
from app.db.database import get_db
from app.db.models.user import User
from app.dependencies.auth_dep import get_user_from_request, require_admin
from app.repositories import users
from app.schemas.admin import AuditLogFilter
from app.schemas.auth import LoginRequest
from app.services import audit, auth
from app.ui.templates import templates

logger = logging.getLogger("pages")

router = APIRouter()


def _redirect_for_user(user: User) -> RedirectResponse:
    """Redirige al usuario según su rol: admin → /dashboard, resto → /chat."""
    if user.role == UserRole.ADMIN:
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/chat", status_code=302)


@router.get("/")
async def root(
    request: Request,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Redirige por rol si hay sesión activa, a /login en caso contrario."""
    if not request.cookies.get("access_token"):
        return RedirectResponse(url="/login", status_code=302)

    try:
        user = get_user_from_request(request, db)
    except InvalidCredentialsError:
        return RedirectResponse(url="/login", status_code=302)
    return _redirect_for_user(user)


@router.get("/login", response_class=HTMLResponse, response_model=None)
async def login_page(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Muestra el formulario de login; redirige por rol si ya hay sesión activa."""
    if not request.cookies.get("access_token"):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"request": request},
        )

    try:
        user = get_user_from_request(request, db)
    except InvalidCredentialsError:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"request": request},
        )
    return _redirect_for_user(user)


@router.post("/login")
@limiter.limit("5/5minute")
async def login_post(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """
    Éxito → HX-Redirect a /chat o /dashboard según rol + cookies de sesión.
    Fallo  → re-render del formulario con mensaje de error.
    """
    form = await request.form()
    username_value = form.get("username")
    username = username_value.strip() if isinstance(username_value, str) else ""
    credential_value = form.get("credential")
    credential = credential_value if isinstance(credential_value, str) else ""

    if not username or not credential:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "request": request,
                "error": "Usuario y credencial son obligatorios.",
            },
        )

    try:
        access_token, refresh_token = auth.login(
            LoginRequest(username=username, credential=credential),
            db,
        )
    except InvalidCredentialsError:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "request": request,
                "error": "Credenciales inválidas.",
            },
        )

    user = users.get_by_username(username, db)
    redirect_url = "/dashboard" if user and user.role == UserRole.ADMIN else "/chat"

    response = Response(status_code=200)
    response.headers["HX-Redirect"] = redirect_url
    set_auth_cookies(response, access_token, refresh_token)
    return response


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
) -> HTMLResponse:
    """
    Usuario normal → 403, sin sesión → 401 vía los handlers de excepción.
    """
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "user": current_user,
        },
    )


# Etiquetas en español para valores técnicos de logs de auditoría.
# Se pasan al template para mostrar texto legible sin perder las clases CSS.
_ACTION_LABELS: dict[str, str] = {
    "allow": "Permitida",
    "mask": "Enmascarada",
    "block": "Bloqueada",
    "error": "Error",
}

_STATUS_LABELS: dict[str, str] = {
    "success": "Correcto",
    "provider_error": "Error del proveedor",
}


@router.get("/dashboard/logs", response_class=HTMLResponse)
async def audit_logs_page(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Muestra los últimos 50 logs de auditoría (solo metadatos)."""
    filter_ = AuditLogFilter(page=1, page_size=50)
    result = audit.list_logs(filter_, db)
    return templates.TemplateResponse(
        request=request,
        name="audit_logs.html",
        context={
            "request": request,
            "user": current_user,
            "logs": result.items,
            "total": result.total,
            "action_labels": _ACTION_LABELS,
            "status_labels": _STATUS_LABELS,
        },
    )
