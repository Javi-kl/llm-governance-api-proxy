from fastapi.testclient import TestClient

from app.core.enums import UserRole
from app.db.models.user import User
from tests.conftest import create_token


def test_given_valid_data_then_returns_201(client: TestClient, admin_user):
    login_response = client.post(
        "/api/v1/admin/auth/login",
        data={"username": "admin", "password": "admin12345"},
    )
    client.cookies = login_response.cookies

    response = client.post(
        "/api/v1/admin/users/register", json={"username": "newuser", "pin": "12345"}
    )

    assert response.status_code == 201
    assert response.json()["username"] == "newuser"


# ── GET /admin/users ──────────────────────────────────────


def test_given_admin_token_then_returns_user_list(
    client: TestClient, admin_user: User, regular_user: User
):
    login_response = client.post(
        "/api/v1/admin/auth/login",
        data={"username": "admin", "password": "admin12345"},
    )
    client.cookies = login_response.cookies

    response = client.get("/api/v1/admin/users")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["username"] == "testuser"
    assert body["items"][0]["role"] == "user"


def test_given_regular_user_token_then_returns_403(
    client: TestClient, regular_user: User
):
    token = create_token("testuser", UserRole.USER)
    client.cookies = {"access_token": token}

    response = client.get("/api/v1/admin/users")

    assert response.status_code == 403


def test_given_no_auth_then_returns_401(client: TestClient):
    response = client.get("/api/v1/admin/users")

    assert response.status_code == 401
