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
