"""Tests de integración HTTP para la gestión web de usuarios."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import security
from app.core.enums import UserRole
from app.db.models.user import User
from app.repositories import users
from tests.conftest import create_token


# ═══════════════════════════════════════════════════════════
# GET /dashboard/users
# ═══════════════════════════════════════════════════════════


def test_given_no_cookie_then_users_page_returns_401(client: TestClient):
    response = client.get("/dashboard/users", follow_redirects=False)

    assert response.status_code == 401


def test_given_regular_user_then_users_page_returns_403(
    client: TestClient, regular_user: User
):
    token = create_token(regular_user.id, regular_user.role)
    client.cookies.set("access_token", token)

    response = client.get("/dashboard/users", follow_redirects=False)

    assert response.status_code == 403


def test_given_admin_user_then_users_page_renders_user_management(
    client: TestClient, admin_user: User, regular_user: User
):
    token = create_token(admin_user.id, admin_user.role)
    client.cookies.set("access_token", token)

    response = client.get("/dashboard/users", follow_redirects=False)

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Gestión de usuarios" in response.text
    assert "Crear usuario" in response.text
    assert regular_user.username in response.text
    assert "Activo" in response.text
    assert 'hx-post="/dashboard/users"' in response.text


# ═══════════════════════════════════════════════════════════
# POST /dashboard/users
# ═══════════════════════════════════════════════════════════


def test_given_valid_form_then_create_user_returns_updated_panel(
    client: TestClient, admin_user: User, db_session: Session
):
    token = create_token(admin_user.id, admin_user.role)
    client.cookies.set("access_token", token)

    response = client.post(
        "/dashboard/users",
        data={"username": "newuser", "pin": "12345"},
        follow_redirects=False,
    )

    created_user = users.get_by_username("newuser", db_session)
    assert response.status_code == 200
    assert "Usuario creado correctamente." in response.text
    assert "newuser" in response.text
    assert created_user is not None
    assert created_user.role == UserRole.USER


def test_given_duplicate_username_then_create_user_shows_error(
    client: TestClient, admin_user: User, regular_user: User
):
    token = create_token(admin_user.id, admin_user.role)
    client.cookies.set("access_token", token)

    response = client.post(
        "/dashboard/users",
        data={"username": regular_user.username, "pin": "12345"},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert "Este username ya está registrado." in response.text


def test_given_invalid_pin_then_create_user_shows_validation_error(
    client: TestClient, admin_user: User
):
    token = create_token(admin_user.id, admin_user.role)
    client.cookies.set("access_token", token)

    response = client.post(
        "/dashboard/users",
        data={"username": "newuser", "pin": "abc"},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert "El username debe tener entre 4 y 19 caracteres" in response.text


# ═══════════════════════════════════════════════════════════
# POST /dashboard/users/{user_id}/deactivate
# ═══════════════════════════════════════════════════════════


def test_given_active_user_then_deactivate_returns_updated_panel(
    client: TestClient, admin_user: User, regular_user: User, db_session: Session
):
    token = create_token(admin_user.id, admin_user.role)
    client.cookies.set("access_token", token)

    response = client.post(
        f"/dashboard/users/{regular_user.id}/deactivate",
        follow_redirects=False,
    )

    db_session.refresh(regular_user)
    assert response.status_code == 200
    assert "Usuario desactivado." in response.text
    assert "Inactivo" in response.text
    assert regular_user.active is False


def test_given_admin_target_then_deactivate_shows_error(
    client: TestClient, admin_user: User
):
    token = create_token(admin_user.id, admin_user.role)
    client.cookies.set("access_token", token)

    response = client.post(
        f"/dashboard/users/{admin_user.id}/deactivate",
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert "Los administradores no se gestionan desde este panel." in response.text


# ═══════════════════════════════════════════════════════════
# POST /dashboard/users/{user_id}/pin
# ═══════════════════════════════════════════════════════════


def test_given_valid_pin_then_reset_pin_returns_updated_panel(
    client: TestClient, admin_user: User, regular_user: User, db_session: Session
):
    old_hash = regular_user.credential_hash
    token = create_token(admin_user.id, admin_user.role)
    client.cookies.set("access_token", token)

    response = client.post(
        f"/dashboard/users/{regular_user.id}/pin",
        data={"pin": "99999"},
        follow_redirects=False,
    )

    db_session.refresh(regular_user)
    assert response.status_code == 200
    assert "PIN actualizado." in response.text
    assert regular_user.credential_hash != old_hash
    assert security.verify_password("99999", regular_user.credential_hash) is True
