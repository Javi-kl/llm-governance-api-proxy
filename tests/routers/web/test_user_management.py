"""Tests de integración HTTP para la gestión web de usuarios."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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
    assert "Gestión de usuarios" in response.text
    assert regular_user.username in response.text


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
