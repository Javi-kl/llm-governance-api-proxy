from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.core.exceptions import ProviderError, ProviderTimeoutError
from app.core.provider import send


def test_given_messages_array_then_forwards_intact_and_returns_response():
    messages = [
        {"role": "system", "content": "Responde breve."},
        {"role": "user", "content": "¿Capital de Francia?"},
    ]
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "París"}}],
    }

    with patch("httpx.post", return_value=mock_response) as mock_post:
        result = send(messages)

    assert result == "París"
    mock_post.assert_called_once()
    assert mock_post.call_args.kwargs["json"]["messages"] == messages


def test_given_provider_timeout_then_raises():
    with patch("httpx.post", side_effect=httpx.TimeoutException("timeout")):
        with pytest.raises(ProviderTimeoutError):
            send([{"role": "user", "content": "X"}])


def test_given_provider_http_error_then_raises_provider_error():
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "error", request=MagicMock(), response=mock_response
    )

    with patch("httpx.post", return_value=mock_response):
        with pytest.raises(ProviderError) as exc_info:
            send([{"role": "user", "content": "X"}])

    assert exc_info.value.status_code == 500


def test_given_provider_connection_error_then_raises_provider_error():
    with patch("httpx.post", side_effect=httpx.ConnectError("connection refused")):
        with pytest.raises(ProviderError):
            send([{"role": "user", "content": "X"}])


@pytest.mark.parametrize(
    "payload",
    [
        {"no_choices": "estructura inesperada"},
        {"choices": []},
        {"choices": [{"message": {"content": None}}]},
    ],
    ids=[
        "missing_choices",
        "empty_choices",
        "null_content",
    ],
)
def test_given_malformed_response_then_raises_provider_error(payload):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = payload

    with patch("httpx.post", return_value=mock_response):
        with pytest.raises(ProviderError):
            send([{"role": "user", "content": "X"}])


def test_given_invalid_json_then_raises_provider_error():
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.side_effect = ValueError("JSON inválido")

    with patch("httpx.post", return_value=mock_response):
        with pytest.raises(ProviderError):
            send([{"role": "user", "content": "X"}])
