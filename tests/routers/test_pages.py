"""Tests de integración HTTP para las rutas web de pages.py.

Verifican redirects, renderizado de formulario, manejo de errores
y emisión de cookies + header HX-Redirect en login exitoso.
"""

from fastapi.testclient import TestClient

from app.db.models.user import User
from tests.conftest import create_token


# ═══════════════════════════════════════════════════════════
# GET /
# ═══════════════════════════════════════════════════════════


def test_given_no_cookie_then_root_redirects_to_login(client: TestClient):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


def test_given_valid_access_token_cookie_then_root_redirects_to_chat(
    client: TestClient, regular_user: User
):
    token = create_token(regular_user.id, regular_user.role)
    client.cookies.set("access_token", token)

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/chat"


def test_given_invalid_token_cookie_then_root_redirects_to_login(
    client: TestClient,
):
    # Token que no pasa validación de firma JWT
    client.cookies.set("access_token", "esto.no.es.un.jwt.valido")

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


def test_given_admin_cookie_then_root_redirects_to_dashboard(
    client: TestClient, admin_user: User
):
    token = create_token(admin_user.id, admin_user.role)
    client.cookies.set("access_token", token)

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard"


# ═══════════════════════════════════════════════════════════
# GET /login
# ═══════════════════════════════════════════════════════════


def test_given_login_page_then_returns_html_with_username_field(
    client: TestClient,
):
    response = client.get("/login")

    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "text/html" in content_type
    assert 'id="username"' in response.text


def test_given_login_page_with_regular_user_then_redirects_to_chat(
    client: TestClient, regular_user: User
):
    token = create_token(regular_user.id, regular_user.role)
    client.cookies.set("access_token", token)

    response = client.get("/login", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/chat"


def test_given_login_page_with_admin_then_redirects_to_dashboard(
    client: TestClient, admin_user: User
):
    token = create_token(admin_user.id, admin_user.role)
    client.cookies.set("access_token", token)

    response = client.get("/login", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard"


def test_given_login_page_with_invalid_token_then_returns_html_form(
    client: TestClient,
):
    client.cookies.set("access_token", "esto.no.es.un.jwt.valido")

    response = client.get("/login", follow_redirects=False)

    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "text/html" in content_type
    assert 'id="username"' in response.text


# ═══════════════════════════════════════════════════════════
# POST /login — errores
# ═══════════════════════════════════════════════════════════


def test_given_empty_fields_then_returns_html_error(client: TestClient):
    response = client.post("/login", data={"username": "", "credential": ""})

    assert response.status_code == 200
    html = response.text
    assert "error-message" in html
    assert "obligatorios" in html


def test_given_invalid_credentials_then_returns_html_error(
    client: TestClient, regular_user: User
):
    response = client.post(
        "/login",
        data={"username": "testuser", "credential": "wrongpassword"},
    )

    assert response.status_code == 200
    html = response.text
    assert "error-message" in html
    assert "inválidas" in html


# ═══════════════════════════════════════════════════════════
# POST /login — éxito
# ═══════════════════════════════════════════════════════════


def test_given_valid_credentials_then_returns_redirect_with_cookies(
    client: TestClient, regular_user: User
):
    response = client.post(
        "/login",
        data={"username": "testuser", "credential": "123456"},
    )

    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/chat"

    set_cookies = response.headers.get_list("set-cookie")
    combined = "; ".join(set_cookies)
    assert "access_token=" in combined
    assert "refresh_token=" in combined


def test_given_admin_credentials_then_redirects_to_dashboard(
    client: TestClient, admin_user: User
):
    response = client.post(
        "/login",
        data={"username": "admin", "credential": "admin12345"},
    )

    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/dashboard"

    set_cookies = response.headers.get_list("set-cookie")
    combined = "; ".join(set_cookies)
    assert "access_token=" in combined
    assert "refresh_token=" in combined


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
    """Admin autenticado → 200, HTML con navegación, botón de logout y secciones."""
    token = create_token(admin_user.id, admin_user.role)
    client.cookies.set("access_token", token)

    response = client.get("/dashboard", follow_redirects=False)

    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "text/html" in content_type
    assert "Panel de administración" in response.text
    assert "Bienvenido" in response.text
    assert 'href="/chat"' in response.text
    # Navegación: enlace al chat y secciones pendientes
    assert "Ir al chat" in response.text
    assert "Gestión de usuarios" in response.text
    assert "Logs de auditoría" in response.text
    # Botón de logout con HTMX
    assert 'hx-post="/api/v1/auth/logout"' in response.text
    assert "Cerrar sesión" in response.text
