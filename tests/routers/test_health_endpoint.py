from fastapi.testclient import TestClient


def test_given_healthy_then_returns_200(client: TestClient):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["database"] == "connected"
