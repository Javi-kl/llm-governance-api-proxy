"""Rutas de páginas web del proxy: raíz, login y dashboard.

El login web reutiliza auth_service.login() — la misma lógica que la API REST.
En vez de devolver JSON, responde con cookies + HX-Redirect (éxito)
o re-renderiza el formulario con error (fallo).

El dashboard está protegido con require_admin: solo usuarios con rol admin
pueden acceder. Usuario normal → 403, sin sesión → 401.
"""

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
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


# ── helpers de renderizado ────────────────────────────────────────────


def _render_template(
    request: Request,
    template_name: str,
    **context,
) -> HTMLResponse:
    """Renderiza un template Jinja2 con 'request' siempre en el contexto."""
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context={
            "request": request,
            **context,
        },
    )


def _render_login(
    request: Request,
    error: str | None = None,
) -> HTMLResponse:
    """Renderiza la página de login con un mensaje de error opcional."""
    if error is None:
        return _render_template(request, "login.html")
    return _render_template(request, "login.html", error=error)


# ── helpers de negocio ────────────────────────────────────────────────


def _redirect_for_user(user: User) -> RedirectResponse:
    """Redirige al usuario según su rol: admin → /dashboard, resto → /chat."""
    if user.role == UserRole.ADMIN:
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/chat", status_code=302)


# ── endpoints ─────────────────────────────────────────────────────────


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
        return _render_login(request)

    try:
        user = get_user_from_request(request, db)
    except InvalidCredentialsError:
        return _render_login(request)
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
        return _render_login(request, error="Usuario y credencial son obligatorios.")

    try:
        access_token, refresh_token = auth.login(
            LoginRequest(username=username, credential=credential),
            db,
        )
    except InvalidCredentialsError:
        return _render_login(request, error="Credenciales inválidas.")

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
    return _render_template(
        request,
        "dashboard.html",
        user=current_user,
    )


# ── constantes de logs de auditoría ───────────────────────────────────

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

# Acciones válidas para filtros de auditoría.
_VALID_ACTIONS: set[str] = {"allow", "mask", "block", "error"}

# Opciones visibles del selector de acción en el formulario de filtros.
_ACTION_OPTIONS: list[tuple[str, str]] = [
    ("", "Todas"),
    ("allow", "Permitida"),
    ("mask", "Enmascarada"),
    ("block", "Bloqueada"),
    ("error", "Error"),
]


# ── helpers de parseo de filtros ──────────────────────────────────────


def _empty_to_none(value: str | None) -> str | None:
    """Convierte cadena vacía o solo espacios a None."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _parse_action(value: str | None) -> str | None:
    """Valida acción de auditoría contra _VALID_ACTIONS."""
    cleaned = _empty_to_none(value)
    if cleaned is None:
        return None
    if cleaned not in _VALID_ACTIONS:
        raise ValueError("La acción seleccionada no es válida.")
    return cleaned


def _parse_user_id(value: str | None) -> int | None:
    """Parsea user_id como entero positivo."""
    cleaned = _empty_to_none(value)
    if cleaned is None:
        return None
    try:
        user_id = int(cleaned)
    except (TypeError, ValueError):
        raise ValueError("El usuario debe ser un número entero positivo.")
    if user_id <= 0:
        raise ValueError("El usuario debe ser un número entero positivo.")
    return user_id


def _parse_datetime(value: str | None, label: str) -> datetime | None:
    """Parsea fecha desde ISO 8601. label se usa en el mensaje de error."""
    cleaned = _empty_to_none(value)
    if cleaned is None:
        return None
    try:
        parsed = datetime.fromisoformat(cleaned)
    except (TypeError, ValueError):
        raise ValueError(f"La fecha {label} tiene un formato inválido.")

    # Rechazar fechas con zona horaria porque la UI usa datetime-local (naive)
    # y las comparaciones entre naive/aware lanzan TypeError.
    if parsed.tzinfo is not None:
        raise ValueError(f"La fecha {label} no debe incluir zona horaria.")

    return parsed


def _build_audit_log_filter_from_query(
    action: str | None,
    user_id: str | None,
    date_from: str | None,
    date_to: str | None,
) -> tuple[AuditLogFilter, dict[str, str], str | None]:
    """
    Devuelve:
    - AuditLogFilter: objeto con los filtros parseados (fallback sin filtros si hay error).
    - dict[str, str]: valores normalizados para repintar el formulario.
    - str | None: mensaje de error si algún filtro es inválido, None si todo ok.
    """
    selected_filters: dict[str, str] = {
        "action": _empty_to_none(action) or "",
        "user_id": _empty_to_none(user_id) or "",
        "date_from": _empty_to_none(date_from) or "",
        "date_to": _empty_to_none(date_to) or "",
    }

    filter_error: str | None = None

    try:
        parsed_action = _parse_action(action)
        parsed_user_id = _parse_user_id(user_id)
        parsed_date_from = _parse_datetime(date_from, "desde")
        parsed_date_to = _parse_datetime(date_to, "hasta")

        # Validación de rango de fechas
        if parsed_date_from and parsed_date_to and parsed_date_from > parsed_date_to:
            raise ValueError("La fecha desde no puede ser posterior a la fecha hasta.")

        filter_ = AuditLogFilter(
            page=1,
            page_size=50,
            action=parsed_action,
            user_id=parsed_user_id,
            date_from=parsed_date_from,
            date_to=parsed_date_to,
        )
    except ValueError as exc:
        filter_error = str(exc)
        filter_ = AuditLogFilter(page=1, page_size=50)

    return filter_, selected_filters, filter_error


@router.get("/dashboard/logs", response_class=HTMLResponse)
async def audit_logs_page(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
    action: str | None = Query(None),
    user_id: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
) -> HTMLResponse:
    """Muestra los últimos 50 logs de auditoría (solo metadatos), con filtros opcionales vía GET."""
    filter_, selected_filters, filter_error = _build_audit_log_filter_from_query(
        action, user_id, date_from, date_to
    )
    result = audit.list_logs(filter_, db)

    return _render_template(
        request,
        "audit_logs.html",
        user=current_user,
        logs=result.items,
        total=result.total,
        action_labels=_ACTION_LABELS,
        status_labels=_STATUS_LABELS,
        action_options=_ACTION_OPTIONS,
        selected_filters=selected_filters,
        filter_error=filter_error,
    )
