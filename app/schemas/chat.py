from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.enums import MessageRole

MAX_LEN_CONTENT = 16000
MAX_LEN_MESSAGES = 20


class MessageItem(BaseModel):
    role: MessageRole
    content: str

    @field_validator("content")
    @classmethod
    def _max_len_content(cls, content: str) -> str:
        if len(content) > MAX_LEN_CONTENT:
            raise ValueError("Has alcanzado el limite de caracteres")
        return content


class ChatRequest(BaseModel):
    # Cualquier campo no declarado -> 422 (rechaza typos del cliente).
    model_config = ConfigDict(extra="forbid")

    messages: list[MessageItem]

    @field_validator("messages")
    @classmethod
    def _at_least_one_user_message(
        cls, messages: list[MessageItem]
    ) -> list[MessageItem]:
        if not any(m.role == MessageRole.USER for m in messages):
            raise ValueError(
                "El array 'messages' debe contener al menos un mensaje con rol 'user'"
            )
        return messages

    @field_validator("messages")
    @classmethod
    def _len_max_limit_messages(cls, messages: list[MessageItem]) -> list[MessageItem]:
        if len(messages) > MAX_LEN_MESSAGES:
            raise ValueError("Has alcanzado el limite de mensajes para esta sesion.")
        return messages


class ChatResponse(BaseModel):
    request_id: str
    action: Literal["allow", "mask", "block", "error"]
    message: MessageItem | None  # None en block/error
    detected_categories: list[str]  # [] si no hubo detecciones
    reason: str | None  # Solo en block/error
