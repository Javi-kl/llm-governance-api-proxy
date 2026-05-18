from http.cookies import SimpleCookie

from fastapi.testclient import TestClient

from app.db.models.user import User

# ── POST /api/v1/auth/login ───────────────────────────────


def test_given_valid_user_credentials_then_returns_200_and_cookie(
    client: TestClient, regular_user: User
):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "credential": "123456"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "login correcto"
    assert "access_token" in response.cookies


def test_given_valid_admin_credentials_then_returns_200_and_cookie(
    client: TestClient, admin_user: User
):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "credential": "admin12345"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "login correcto"
    assert "access_token" in response.cookies


def test_given_nonexistent_user_then_returns_401(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "ghost", "credential": "123456"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales no válidas"


def test_given_wrong_credential_then_returns_401(
    client: TestClient, regular_user: User
):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "credential": "999999"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales no válidas"


def test_given_inactive_user_then_returns_401(
    client: TestClient, regular_user: User, db_session
):
    regular_user.active = False
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "credential": "123456"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales no válidas"


def test_given_missing_credential_field_then_returns_422(
    client: TestClient, regular_user: User
):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser"},
    )

    assert response.status_code == 422


def test_given_login_cookie_then_works_with_auth_dep(
    client: TestClient, regular_user: User
):
    # Hacer login
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "credential": "123456"},
    )
    assert login_response.status_code == 200

    # Usar la cookie en un endpoint protegido
    # (admin/users requiere admin — user normal recibe 403, no 401)
    client.cookies = login_response.cookies
    response = client.get("/api/v1/admin/users")

    # 403 = autenticado pero sin permisos (no 401 = no autenticado)
    assert response.status_code == 403


def test_given_login_then_cookie_has_security_attributes(
    client: TestClient, regular_user: User
):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "credential": "123456"},
    )
    assert response.status_code == 200
    set_cookie_header = response.headers.get("set-cookie", "")
    cookie = SimpleCookie()
    cookie.load(set_cookie_header)
    assert "access_token" in cookie
    assert "httponly" in cookie["access_token"]  # flag presente = True
    assert cookie["access_token"]["samesite"] == "lax"
    assert cookie["access_token"]["path"] == "/"


# ------ Logout --------------------------
def test_given_authenticated_user_then_logout_deletes_cookie(
    client: TestClient, regular_user: User
):
    client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "credential": "123456"},
    )
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert "Max-Age=0" in response.headers.get("set-cookie", "")
