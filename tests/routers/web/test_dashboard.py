"""Tests de integración HTTP para la ruta web de dashboard."""

from fastapi.testclient import TestClient

from app.db.models.user import User
from tests.conftest import create_token


# ═══════════════════════════════════════════════════════════
# GET /dashboard
# ═══════════════════════════════════════════════════════════


def test_given_no_cookie_then_dashboard_returns_401(client: TestClient):
    """Sin sesión, el handler de InvalidCredentialsError responde 401."""
    response = client.get("/dashboard", follow_redirects=False)

    assert response.status_code == 401


def test_given_regular_user_then_dashboard_returns_403(
    client: TestClient, regular_user: User
):
    """Usuario normal autenticado → require_admin lanza PermissionDeniedError (403)."""
    token = create_token(regular_user.id, regular_user.role)
    client.cookies.set("access_token", token)

    response = client.get("/dashboard", follow_redirects=False)

    assert response.status_code == 403


def test_given_admin_user_then_dashboard_returns_html(
    client: TestClient, admin_user: User
):
    """Admin autenticado → 200, HTML con navegación a /dashboard/logs, botón de logout y secciones."""
    token = create_token(admin_user.id, admin_user.role)
    client.cookies.set("access_token", token)

    response = client.get("/dashboard", follow_redirects=False)

    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "text/html" in content_type
    assert "Panel de administración" in response.text
    assert "Bienvenido" in response.text
    assert 'href="/chat"' in response.text
    # Navegación: enlace al chat, logs de auditoría, y secciones pendientes
    assert "Ir al chat" in response.text
    assert "Gestión de usuarios" in response.text
    assert "Logs de auditoría" in response.text
    assert 'href="/dashboard/logs"' in response.text
    # Botón de logout con HTMX
    assert 'hx-post="/api/v1/auth/logout"' in response.text
    assert "Cerrar sesión" in response.text
