"""Helpers comunes de renderizado y redirección para las rutas web."""

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.enums import UserRole
from app.db.models.user import User
from app.ui.templates import templates


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


def _render_landing(request: Request) -> HTMLResponse:
    """Renderiza la landing pública."""
    return _render_template(request, "landing.html")


def _redirect_for_user(user: User) -> RedirectResponse:
    """Redirige al usuario según su rol: admin → /dashboard, resto → /chat."""
    if user.role == UserRole.ADMIN:
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/chat", status_code=302)
