"""Tests unitarios para el callback _chat_handler() del borde Gradio.

Verifica que los errores del proveedor se manejen con el mensaje específico
y que los errores inesperados no expongan detalles técnicos al usuario.
"""

from unittest.mock import MagicMock, patch

import gradio as gr

from app.core.enums import MessageRole
from app.core.exceptions import ProviderError, ProviderTimeoutError
from app.ui.gradio_chat import (
    _chat_handler,
    _extract_text_content,
    _history_to_messages,
)
from app.ui.gradio_config import AUTH_ERROR_MESSAGE, PROVIDER_ERROR_MESSAGE


def _mock_request(username: str | None = None) -> MagicMock:
    """Factory de mock de gr.Request con username configurable."""
    req = MagicMock(spec=gr.Request)
    req.username = username
    return req


def _mock_db_context() -> tuple[MagicMock, MagicMock]:
    """Devuelve (mock_context_manager, mock_db_session) para get_db_context."""
    mock_db = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_db
    return mock_ctx, mock_db


def test_given_missing_username_then_returns_auth_error():
    """Un usuario sin request.username recibe el mensaje de error de autenticación."""
    request = _mock_request(username=None)

    result = _chat_handler("hola", [], request)

    assert result == AUTH_ERROR_MESSAGE


def test_given_provider_timeout_then_returns_provider_message():
    """ProviderError desde process_chat devuelve mensaje genérico de proveedor."""
    mock_ctx, _mock_db = _mock_db_context()
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.active = True
    mock_user.username = "testuser"

    with (
        patch(
            "app.ui.gradio_chat.get_db_context", return_value=mock_ctx
        ) as mock_get_db,
        patch("app.ui.gradio_chat.users") as mock_users,
        patch(
            "app.ui.gradio_chat.process_chat",
            side_effect=ProviderTimeoutError(),
        ) as mock_process_chat,
    ):
        mock_users.get_by_id.return_value = mock_user

        request = _mock_request(username="1")
        result = _chat_handler("hola", [], request)

    mock_get_db.assert_called_once()
    mock_users.get_by_id.assert_called_once()
    mock_process_chat.assert_called_once()
    assert result == PROVIDER_ERROR_MESSAGE


def test_given_provider_error_then_returns_provider_message():
    """Variante con ProviderError (sin status code)."""
    mock_ctx, _mock_db = _mock_db_context()
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.active = True
    mock_user.username = "testuser"

    with (
        patch("app.ui.gradio_chat.get_db_context", return_value=mock_ctx),
        patch("app.ui.gradio_chat.users") as mock_users,
        patch("app.ui.gradio_chat.process_chat", side_effect=ProviderError()),
    ):
        mock_users.get_by_id.return_value = mock_user

        request = _mock_request(username="1")
        result = _chat_handler("hola", [], request)

    assert result == PROVIDER_ERROR_MESSAGE


def test_given_unexpected_user_lookup_error_then_returns_generic_message():
    """Error inesperado (ej. fallo de BD en users.get_by_id) → mensaje genérico."""
    mock_ctx, _mock_db = _mock_db_context()

    with (
        patch("app.ui.gradio_chat.get_db_context", return_value=mock_ctx),
        patch("app.ui.gradio_chat.users") as mock_users,
    ):
        mock_users.get_by_id.side_effect = RuntimeError("connection refused")

        request = _mock_request(username="1")
        result = _chat_handler("hola", [], request)

    # No debe propagar la excepción.
    assert result == PROVIDER_ERROR_MESSAGE


def test_given_unexpected_error_then_does_not_expose_technical_details():
    """El mensaje devuelto ante error inesperado es el genérico, no la traza."""
    mock_ctx, _mock_db = _mock_db_context()

    with (
        patch("app.ui.gradio_chat.get_db_context", return_value=mock_ctx),
        patch("app.ui.gradio_chat.users") as mock_users,
    ):
        mock_users.get_by_id.side_effect = RuntimeError(
            "detalle técnico sensible no debe exponerse"
        )

        request = _mock_request(username="1")
        result = _chat_handler("hola", [], request)

    assert result == PROVIDER_ERROR_MESSAGE
    # El mensaje genérico no debe contener el detalle técnico.
    assert "detalle técnico" not in result
    assert "RuntimeError" not in result


# ──────────────────────────────────────────────
# Tests unitarios para _extract_text_content()
# ──────────────────────────────────────────────


def test_given_string_content_then_extracts_same_text():
    """Dado contenido str, devuelve el mismo texto sin modificar."""
    result = _extract_text_content("Hola mundo")
    assert result == "Hola mundo"


def test_given_gradio_text_blocks_then_extracts_joined_text():
    """Dado lista de bloques de texto al estilo Gradio 6, extrae y une el texto."""
    content = [
        {"type": "text", "text": "Hola"},
        {"type": "text", "text": "Mundo"},
    ]
    result = _extract_text_content(content)
    assert result == "Hola\nMundo"


def test_given_mixed_blocks_then_ignores_invalid_content():
    """Dado contenido mixto/no textual, ignora bloques inválidos y no rompe."""
    content = [
        {"type": "text", "text": "Válido"},
        "string suelto",
        {"type": "image", "url": "http://example.com/img.png"},
        {"type": "text", "text": "También válido"},
        None,
    ]
    result = _extract_text_content(content)
    assert result == "Válido\nTambién válido"


# ──────────────────────────────────────────────
# Tests unitarios para _history_to_messages()
# ──────────────────────────────────────────────


def test_given_history_then_converts_roles_to_message_items():
    """Dado historial con turnos user y assistant, convierte a MessageItem con roles correctos."""
    history = [
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "¡Hola! ¿En qué puedo ayudarte?"},
    ]

    result = _history_to_messages("Segundo mensaje", history)

    assert len(result) == 3
    assert result[0].role == MessageRole.USER
    assert result[0].content == "Hola"
    assert result[1].role == MessageRole.ASSISTANT
    assert result[1].content == "¡Hola! ¿En qué puedo ayudarte?"
    assert result[2].role == MessageRole.USER
    assert result[2].content == "Segundo mensaje"


def test_given_new_message_then_appends_user_message():
    """El nuevo mensaje se añade siempre al final como rol USER."""
    history: list[dict] = []

    result = _history_to_messages("Hola", history)

    assert len(result) == 1
    assert result[0].role == MessageRole.USER
    assert result[0].content == "Hola"


def test_given_empty_or_unknown_turns_then_skips_them():
    """Ignora turnos con contenido vacío o rol desconocido, sin romper."""
    history = [
        {"role": "user", "content": ""},  # contenido vacío → omitido
        {"role": "system", "content": "Instrucción"},  # rol no soportado → omitido
        {"role": "user", "content": "Hola"},
        {"role": "unknown", "content": "Mensaje"},  # rol desconocido → omitido
        {"role": "assistant", "content": "Respuesta"},
        {"role": "user", "content": None},  # content None → extract retorna ""
    ]

    result = _history_to_messages("Nuevo mensaje", history)

    assert len(result) == 3
    assert result[0].role == MessageRole.USER
    assert result[0].content == "Hola"
    assert result[1].role == MessageRole.ASSISTANT
    assert result[1].content == "Respuesta"
    assert result[2].role == MessageRole.USER
    assert result[2].content == "Nuevo mensaje"
