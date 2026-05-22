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
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["error"]["message"] == "Credenciales no válidas"


def test_given_wrong_credential_then_returns_401(
    client: TestClient, regular_user: User
):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "credential": "999999"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["error"]["message"] == "Credenciales no válidas"


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
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["error"]["message"] == "Credenciales no válidas"


def test_given_missing_credential_field_then_returns_422(
    client: TestClient, regular_user: User
):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "La solicitud contiene datos inválidos"
    assert "details" in body["error"]
    fields = [d["field"] for d in body["error"]["details"]]
    assert "credential" in fields


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
    set_cookies = response.headers.get_list("set-cookie")
    assert len(set_cookies) == 2
    
    # Parsear el de access_token
    access_cookie = SimpleCookie()
    access_cookie.load(set_cookies[0])
    assert "access_token" in access_cookie
    assert "httponly" in access_cookie["access_token"]  # flag presente = True
    assert access_cookie["access_token"]["samesite"] == "lax"
    assert access_cookie["access_token"]["path"] == "/"


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
    
    set_cookies = response.headers.get_list("set-cookie")
    assert any("Max-Age=0" in c and "access_token" in c for c in set_cookies)
    assert any("Max-Age=0" in c and "refresh_token" in c for c in set_cookies)
