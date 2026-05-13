from fastapi.testclient import TestClient


def test_given_valid_credentials_then_returns_200(
    client: TestClient, admin_user
):
    response = client.post(
        "/api/v1/admin/auth/login",
        data={"username": "admin", "password": "admin12345"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "login correcto"
    assert "access_token" in response.cookies
