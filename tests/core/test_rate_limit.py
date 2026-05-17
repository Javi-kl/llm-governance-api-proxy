from fastapi.testclient import TestClient


# ── Rate limiting en endpoints de autenticación ───────────────


def test_given_login_limit_exceeded_then_returns_429(client: TestClient):
    """Hace 6 requests a login, la 6ª devuelve 429."""
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "ghost", "credential": "x"},
        )
        # Las primeras 5 pueden ser 401 (credenciales inválidas)
        assert response.status_code in (401, 429)

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "ghost", "credential": "x"},
    )
    assert response.status_code == 429


def test_given_change_password_limit_exceeded_then_returns_429(
    client: TestClient, admin_user
):
    """Hace 2 requests a change_password, la 2ª devuelve 429."""
    # Login como admin
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "credential": "admin12345"},
    )
    assert login_response.status_code == 200

    # Primera request a change_password — cuenta para el rate limit
    # (puede devolver 400 por contraseña actual incorrecta)
    client.patch(
        "/api/v1/auth/password",
        json={
            "current_password": "wrong",
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!",
        },
    )

    # Segunda request — debe ser 429 por límite de 1/minuto
    response = client.patch(
        "/api/v1/auth/password",
        json={
            "current_password": "wrong",
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!",
        },
    )
    assert response.status_code == 429
