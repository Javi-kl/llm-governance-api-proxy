from typing import Annotated
import time

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.services.chat import process_chat_completion
from app.db.models.user import User
from app.db.database import get_db
from app.schemas.chat import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatResponse,
    MessageItem,
)
from app.core.enums import MessageRole
from app.dependencies.api_key_auth_dep import api_key_auth_dep

router = APIRouter(prefix="/chat/completions", tags=["openai"])


@router.post(
    "",
    response_model=ChatCompletionResponse,
    status_code=status.HTTP_200_OK,
)
def create_chat_completion(
    request: ChatCompletionRequest,
    current_user: Annotated[User, Depends(api_key_auth_dep)],
    db: Annotated[Session, Depends(get_db)],
) -> ChatCompletionResponse:

    result = process_chat_completion(request.messages, request.model, current_user, db)

    return _adapt_to_chat_completion_response(result, request)


def _adapt_to_chat_completion_response(
    result: ChatResponse, request: ChatCompletionRequest
) -> ChatCompletionResponse:

    if result.action == "block":
        message = MessageItem(
            role=MessageRole.ASSISTANT,
            content="La solicitud ha sido bloqueada por la politica de seguridad.",
        )
        finish_reason = "content_filter"

    else:
        if result.message is None:
            raise RuntimeError("El procesamiento no devolvió ningún mensaje")

        message = result.message
        finish_reason = "stop"

    return ChatCompletionResponse(
        id=f"chatcmpl-{result.request_id}",
        created=int(time.time()),
        model=request.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=message,
                finish_reason=finish_reason,
            )
        ],
    )
