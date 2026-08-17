from unittest.mock import patch
import pytest

from urllib.parse import urlparse
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ProviderError, ProviderTimeoutError
from app.schemas.chat import MessageItem, MessageRole, ChatResponse
from app.db.models.user import User
from app.services.policy import PRIVACY_SYSTEM_PROMPT
from app.services.api_keys import create_for_user


@pytest.fixture
def api_key_headers(
    regular_user: User,
    db_session: Session,
) -> dict[str, str]:

    raw_key = create_for_user(
        regular_user.username,
        "chat endpoint tests",
        db_session,
    )
    db_session.commit()

    return {"Authorization": f"Bearer {raw_key}"}


def test_given_no_api_key_then_returns_401(client: TestClient):
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": get_settings().LLM_MODEL,
            "messages": [{"role": "user", "content": "hola"}],
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["type"] == "authentication_error"
    assert response.json()["error"]["code"] is None
    assert response.json()["error"]["param"] is None


def test_given_empty_messages_array_then_returns_422(
    client: TestClient,
    api_key_headers: dict[str, str],
):
    response = client.post(
        "/v1/chat/completions",
        headers=api_key_headers,
        json={
            "model": get_settings().LLM_MODEL,
            "messages": [],
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["type"] == "invalid_request_error"
    assert body["error"]["param"] == "messages"


def test_given_clean_messages_then_returns_allow(
    client: TestClient,
    api_key_headers: dict[str, str],
):

    with patch("app.services.chat.provider_send", return_value="París"):
        response = client.post(
            "/v1/chat/completions",
            headers=api_key_headers,
            json={
                "model": get_settings().LLM_MODEL,
                "messages": [{"role": "user", "content": "¿Capital de Francia?"}],
            },
        )

    assert response.status_code == 200
    body = response.json()
    choice = body["choices"][0]

    assert body["object"] == "chat.completion"
    assert body["id"].startswith("chatcmpl-")
    assert body["model"] == get_settings().LLM_MODEL
    assert choice["message"]["content"] == "París"
    assert choice["message"]["role"] == "assistant"
    assert choice["finish_reason"] == "stop"


def test_given_email_then_masks_before_forwarding(
    client: TestClient,
    api_key_headers: dict[str, str],
):
    with patch("app.services.chat.provider_send", return_value="OK") as mock:
        response = client.post(
            "/v1/chat/completions",
            headers=api_key_headers,
            json={
                "model": get_settings().LLM_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": "Escribe a j@x.com",
                    }
                ],
            },
        )

    assert response.status_code == 200
    body = response.json()
    choice = body["choices"][0]

    assert body["object"] == "chat.completion"
    assert choice["message"]["role"] == "assistant"
    assert choice["message"]["content"] == "OK"
    assert choice["finish_reason"] == "stop"

    sent = mock.call_args.args[0]
    assert sent[0] == {"role": "system", "content": PRIVACY_SYSTEM_PROMPT}
    assert sent[1] == {"role": "user", "content": "Escribe a [EMAIL]"}


def test_given_iban_in_message_then_returns_block(
    client: TestClient,
    api_key_headers: dict[str, str],
):
    with patch("app.services.chat.provider_send") as mock:
        response = client.post(
            "/v1/chat/completions",
            headers=api_key_headers,
            json={
                "model": get_settings().LLM_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": "Mi cuenta es ES9121000418450200051332",
                    }
                ],
            },
        )

    mock.assert_not_called()
    assert response.status_code == 200
    body = response.json()
    choice = body["choices"][0]

    assert choice["message"]["role"] == "assistant"
    assert "bloqueada" in choice["message"]["content"]

    assert choice["finish_reason"] == "content_filter"


def test_given_provider_timeout_then_returns_504(
    client: TestClient,
    api_key_headers: dict[str, str],
):
    with patch("app.services.chat.provider_send", side_effect=ProviderTimeoutError()):
        response = client.post(
            "/v1/chat/completions",
            headers=api_key_headers,
            json={
                "model": get_settings().LLM_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": "¿Capital de Francia?",
                    }
                ],
            },
        )

    assert response.status_code == 504
    body = response.json()

    assert body["error"]["type"] == "api_error"
    assert "proveedor" in body["error"]["message"].lower()


def test_given_provider_error_then_returns_502(
    client: TestClient,
    api_key_headers: dict[str, str],
):

    with patch("app.services.chat.provider_send", side_effect=ProviderError()):
        response = client.post(
            "/v1/chat/completions",
            headers=api_key_headers,
            json={
                "model": get_settings().LLM_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": "¿Capital de Francia?",
                    }
                ],
            },
        )

    assert response.status_code == 502
    body = response.json()
    assert body["error"]["type"] == "api_error"
    assert "proveedor" in body["error"]["message"].lower()


def test_given_non_bearer_scheme_then_return_401(
    client: TestClient,
):
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Basic abc123"},
        json={
            "model": get_settings().LLM_MODEL,
            "messages": [{"role": "user", "content": "hola"}],
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["type"] == "authentication_error"


def test_given_unsupported_model_then_returns_404_without_processing_chat(
    client: TestClient,
    api_key_headers: dict[str, str],
):
    unsupported_model = f"{get_settings().LLM_MODEL}-unsupported"

    with patch("app.services.chat.process_chat") as mock_process_chat:
        response = client.post(
            "/v1/chat/completions",
            headers=api_key_headers,
            json={
                "model": unsupported_model,
                "messages": [{"role": "user", "content": "Hola"}],
            },
        )

    assert response.status_code == 404
    assert response.json()["error"]["type"] == "not_found_error"
    mock_process_chat.assert_not_called()


def test_given_chat_limit_exceeded_then_returns_429(
    client: TestClient,
    api_key_headers: dict[str, str],
):
    payload = {
        "model": get_settings().LLM_MODEL,
        "messages": [{"role": "user", "content": "Hola"}],
    }
    chat_result = ChatResponse(
        request_id="rate-limit-test",
        action="allow",
        message=MessageItem(
            role=MessageRole.ASSISTANT,
            content="OK",
        ),
        detected_categories=[],
        reason=None,
    )
    with patch(
        "app.routers.chat.process_chat_completion",
        return_value=chat_result,
    ) as mock_process_chat:
        for _ in range(10):
            response = client.post(
                "/v1/chat/completions",
                headers=api_key_headers,
                json=payload,
            )
            assert response.status_code == 200
        response = client.post(
            "/v1/chat/completions",
            headers=api_key_headers,
            json=payload,
        )
    assert response.status_code == 429
    assert response.json()["error"]["type"] == "rate_limit_error"
    assert mock_process_chat.call_count == 10


def test_given_valid_api_key_then_lists_configured_model(
    client: TestClient,
    api_key_headers: dict[str, str],
):
    response = client.get(
        "/v1/models",
        headers=api_key_headers,
    )

    assert response.status_code == 200
    body = response.json()

    assert body["object"] == "list"
    assert len(body["data"]) == 1

    data = body["data"][0]
    assert data["id"] == get_settings().LLM_MODEL
    assert data["object"] == "model"
    assert isinstance(data["created"], int)

    expected = urlparse(str(get_settings().LLM_BASE_URL)).hostname or "unknown"
    assert data["owned_by"] == expected


def test_given_configured_model_then_retrieve_returns_bare_model(
    client: TestClient,
    api_key_headers: dict[str, str],
):
    response = client.get(
        f"/v1/models/{get_settings().LLM_MODEL}",
        headers=api_key_headers,
    )
    assert response.status_code == 200
    body = response.json()

    assert body["id"] == get_settings().LLM_MODEL
    assert body["object"] == "model"
    assert isinstance(body["created"], int)

    expected = urlparse(str(get_settings().LLM_BASE_URL)).hostname or "unknown"
    assert body["owned_by"] == expected


def test_given_unknown_model_then_returns_404(
    client: TestClient,
    api_key_headers: dict[str, str],
):
    response = client.get(
        f"/v1/models/{get_settings().LLM_MODEL}-unsupported",
        headers=api_key_headers,
    )

    assert response.status_code == 404
    assert response.json()["error"]["type"] == "not_found_error"


def test_given_multiple_calls_then_created_stays_stable(
    client: TestClient,
    api_key_headers: dict[str, str],
):
    response_1 = client.get(
        "/v1/models",
        headers=api_key_headers,
    )

    response_2 = client.get(
        "/v1/models",
        headers=api_key_headers,
    )

    data_body_1 = response_1.json()["data"][0]
    data_body_2 = response_2.json()["data"][0]
    created_1 = data_body_1["created"]
    created_2 = data_body_2["created"]

    assert created_1 == created_2
