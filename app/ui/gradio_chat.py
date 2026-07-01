"""
Convierte el historial de Gradio al formato MessageItem del backend
y llama a process_chat() — sin duplicar lógica de negocio ni de auth.
"""

import logging

import gradio as gr

from app.core.enums import MessageRole
from app.core.exceptions import ProviderError, ProviderTimeoutError
from app.db.database import get_db_context
from app.repositories import users
from app.schemas.chat import MessageItem
from app.services.chat import process_chat
from app.ui.gradio_config import (
    AUTH_ERROR_MESSAGE,
    BLOCK_MESSAGE,
    PROVIDER_ERROR_MESSAGE,
)

logger = logging.getLogger("gradio_chat")


def _extract_text_content(content: object) -> str:
    """Extrae texto desde el formato de historial de Gradio."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                text = block.get("text", "")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return ""


def _history_to_messages(message: str, history: list[dict]) -> list[MessageItem]:
    """Convierte historial de Gradio + nuevo mensaje a lista de MessageItem."""
    messages: list[MessageItem] = []

    for turn in history:
        role_value = turn.get("role", "")
        content = _extract_text_content(turn.get("content", ""))
        if not content:
            continue

        if role_value == "user":
            messages.append(MessageItem(role=MessageRole.USER, content=content))
        elif role_value == "assistant":
            messages.append(MessageItem(role=MessageRole.ASSISTANT, content=content))

    messages.append(MessageItem(role=MessageRole.USER, content=message))
    return messages


def _chat_handler(message: str, history: list[dict], request: gr.Request) -> str:
    """Callback de Gradio ChatInterface. Orquesta la llamada a process_chat()."""
    if not request.username:
        logger.warning("Intento de chat sin usuario autenticado")
        return AUTH_ERROR_MESSAGE

    try:
        with get_db_context() as db:
            user = users.get_by_id(int(request.username), db)
            if user is None or not user.active:
                logger.warning(
                    "Usuario %s no encontrado o inactivo en chat", request.username
                )
                return AUTH_ERROR_MESSAGE

            messages = _history_to_messages(message, history)

            try:
                response = process_chat(messages, user, db)
            except (ProviderError, ProviderTimeoutError):
                logger.exception(
                    "Error del proveedor en chat para usuario %s", user.username
                )
                return PROVIDER_ERROR_MESSAGE

        if response.action == "block":
            return BLOCK_MESSAGE

        return response.message.content if response.message else ""
    except Exception:
        logger.exception("Error inesperado procesando chat de Gradio")
        return PROVIDER_ERROR_MESSAGE


def build_gradio_app() -> gr.Blocks:
    """Construye la app de Gradio con el ChatInterface."""

    with gr.Blocks(title="Chat — LLM Governance Proxy") as demo:
        gr.Markdown("# Chat con Gobernanza")
        # TODO Deuda técnica: el enlace al panel se muestra también a usuarios normales.
        # /dashboard sigue protegido por require_admin.
        gr.HTML(
            """
            <div class="chat-actions">
                <a class="chat-action-link" href="/dashboard">Volver al panel</a>
                <button class="chat-action-button" onclick="window.logoutFromChat()">
                    Cerrar sesión
                </button>
            </div>
            """
        )

        gr.ChatInterface(
            fn=_chat_handler,
            chatbot=gr.Chatbot(height="75vh"),
            fill_width=True,
        )
    return demo
