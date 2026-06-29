from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.exceptions import ProviderError, ProviderTimeoutError
from app.db.models.user import User
from app.services.policy import PRIVACY_SYSTEM_PROMPT
from tests.conftest import create_token


def _login_as(client: TestClient, user: User) -> None:
    token = create_token(user.id, user.role)
    client.cookies.set("access_token", token)


def test_given_no_cookie_then_returns_401(client: TestClient, regular_user: User):
    response = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "hola"}]},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_given_empty_messages_array_then_returns_422(
    client: TestClient, regular_user: User
):
    _login_as(client, regular_user)

    response = client.post("/api/v1/chat", json={"messages": []})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "user" in str(body["error"])


def test_given_clean_messages_then_returns_allow(
    client: TestClient, regular_user: User
):
    _login_as(client, regular_user)

    with patch("app.services.chat.provider_send", return_value="París"):
        response = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "¿Capital de Francia?"}]},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "allow"
    assert body["message"]["content"] == "París"
    assert body["message"]["role"] == "assistant"
    assert body["detected_categories"] == []
    assert body["reason"] is None
    assert len(body["request_id"]) == 36


def test_given_email_in_message_then_returns_mask(
    client: TestClient, regular_user: User
):
    _login_as(client, regular_user)

    with patch("app.services.chat.provider_send", return_value="OK") as mock:
        response = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "Escribe a j@x.com"}]},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "mask"
    assert body["detected_categories"] == ["contacto"]
    assert body["message"]["content"] == "OK"

    sent = mock.call_args.args[0]
    assert sent[0] == {"role": "system", "content": PRIVACY_SYSTEM_PROMPT}
    assert sent[1] == {"role": "user", "content": "Escribe a [EMAIL]"}


def test_given_iban_in_message_then_returns_block(
    client: TestClient, regular_user: User
):
    _login_as(client, regular_user)

    with patch("app.services.chat.provider_send") as mock:
        response = client.post(
            "/api/v1/chat",
            json={
                "messages": [
                    {"role": "user", "content": "Mi cuenta es ES9121000418450200051332"}
                ]
            },
        )

    mock.assert_not_called()
    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "block"
    assert body["message"] is None
    assert body["detected_categories"] == ["financiero"]
    assert "financiero" in body["reason"]


def test_given_provider_timeout_then_returns_504(
    client: TestClient, regular_user: User
):
    """RF-8: timeout del proveedor externo → 504 + UPSTREAM_TIMEOUT."""
    _login_as(client, regular_user)

    with patch("app.services.chat.provider_send", side_effect=ProviderTimeoutError()):
        response = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "¿Capital de Francia?"}]},
        )

    assert response.status_code == 504
    body = response.json()
    assert body["error"]["code"] == "UPSTREAM_TIMEOUT"
    assert "proveedor" in body["error"]["message"].lower()


def test_given_provider_error_then_returns_502(client: TestClient, regular_user: User):
    """RF-8: error del proveedor externo → 502 + UPSTREAM_ERROR."""
    _login_as(client, regular_user)

    with patch("app.services.chat.provider_send", side_effect=ProviderError()):
        response = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "¿Capital de Francia?"}]},
        )

    assert response.status_code == 502
    body = response.json()
    assert body["error"]["code"] == "UPSTREAM_ERROR"
    assert "proveedor" in body["error"]["message"].lower()
