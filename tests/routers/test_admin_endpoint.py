from fastapi.testclient import TestClient


def test_given_valid_data_then_returns_201(
    client: TestClient, admin_user
):
    login_response = client.post(
        "/api/v1/admin/auth/login",
        data={"username": "admin", "password": "admin12345"},
    )
    cookies = login_response.cookies

    response = client.post(
        "/api/v1/admin/register",
        json={"username": "newuser", "pin": "12345"},
        cookies=cookies,
    )

    assert response.status_code == 201
    assert response.json()["username"] == "newuser"
