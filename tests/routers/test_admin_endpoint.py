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


# ── PATCH /admin/users/{user_id}/deactivate ───────────────


def test_given_admin_deactivates_user_then_returns_200(
    client: TestClient, admin_user: User, regular_user: User
):
    login_response = client.post(
        "/api/v1/admin/auth/login",
        data={"username": "admin", "password": "admin12345"},
    )
    client.cookies = login_response.cookies

    response = client.patch(f"/api/v1/admin/users/{regular_user.id}/deactivate")

    assert response.status_code == 200
    assert response.json()["message"] == "Usuario desactivado."


def test_given_nonexistent_user_then_returns_404(client: TestClient, admin_user: User):
    login_response = client.post(
        "/api/v1/admin/auth/login",
        data={"username": "admin", "password": "admin12345"},
    )
    client.cookies = login_response.cookies

    response = client.patch("/api/v1/admin/users/9999/deactivate")

    assert response.status_code == 404
    assert response.json()["detail"] == "Usuario no encontrado"


def test_given_admin_target_then_returns_422(client: TestClient, admin_user: User):
    login_response = client.post(
        "/api/v1/admin/auth/login",
        data={"username": "admin", "password": "admin12345"},
    )
    client.cookies = login_response.cookies

    response = client.patch(f"/api/v1/admin/users/{admin_user.id}/deactivate")

    assert response.status_code == 422


def test_given_inactive_user_then_returns_422_on_deactivate(
    client: TestClient, admin_user: User, regular_user: User, db_session
):
    regular_user.active = False
    db_session.commit()

    login_response = client.post(
        "/api/v1/admin/auth/login",
        data={"username": "admin", "password": "admin12345"},
    )
    client.cookies = login_response.cookies

    response = client.patch(f"/api/v1/admin/users/{regular_user.id}/deactivate")

    assert response.status_code == 422


def test_given_regular_user_then_returns_403_on_deactivate(
    client: TestClient, regular_user: User
):
    token = create_token("testuser", UserRole.USER)
    client.cookies = {"access_token": token}

    response = client.patch(f"/api/v1/admin/users/{regular_user.id}/deactivate")

    assert response.status_code == 403


def test_given_no_auth_then_returns_401_on_deactivate(client: TestClient):
    response = client.patch("/api/v1/admin/users/1/deactivate")

    assert response.status_code == 401


# ── PATCH /admin/users/{user_id}/pin ──────────────────────


def test_given_admin_resets_pin_then_returns_200(
    client: TestClient, admin_user: User, regular_user: User
):
    login_response = client.post(
        "/api/v1/admin/auth/login",
        data={"username": "admin", "password": "admin12345"},
    )
    client.cookies = login_response.cookies

    response = client.patch(
        f"/api/v1/admin/users/{regular_user.id}/pin",
        json={"pin": "99999"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "PIN de usuario modificado."


def test_given_nonexistent_user_then_returns_404_on_pin_reset(
    client: TestClient, admin_user: User
):
    login_response = client.post(
        "/api/v1/admin/auth/login",
        data={"username": "admin", "password": "admin12345"},
    )
    client.cookies = login_response.cookies

    response = client.patch(
        "/api/v1/admin/users/9999/pin",
        json={"pin": "99999"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Usuario no encontrado"


def test_given_admin_target_then_returns_422_on_pin_reset(
    client: TestClient, admin_user: User
):
    login_response = client.post(
        "/api/v1/admin/auth/login",
        data={"username": "admin", "password": "admin12345"},
    )
    client.cookies = login_response.cookies

    response = client.patch(
        f"/api/v1/admin/users/{admin_user.id}/pin",
        json={"pin": "99999"},
    )

    assert response.status_code == 422


def test_given_regular_user_then_returns_403_on_pin_reset(
    client: TestClient, regular_user: User
):
    token = create_token("testuser", UserRole.USER)
    client.cookies = {"access_token": token}

    response = client.patch(
        f"/api/v1/admin/users/{regular_user.id}/pin",
        json={"pin": "99999"},
    )

    assert response.status_code == 403


def test_given_no_auth_then_returns_401_on_pin_reset(client: TestClient):
    response = client.patch(
        "/api/v1/admin/users/1/pin",
        json={"pin": "99999"},
    )

    assert response.status_code == 401
