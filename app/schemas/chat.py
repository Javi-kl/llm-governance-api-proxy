from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.enums import MessageRole


class MessageItem(BaseModel):
    role: MessageRole
    content: str


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


class ChatResponse(BaseModel):
    request_id: str
    action: Literal["allow", "mask", "block", "error"]
    message: MessageItem | None  # None en block/error
    detected_categories: list[str]  # [] si no hubo detecciones
    reason: str | None  # Solo en block/error
