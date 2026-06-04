from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.services.chat import process_chat
from app.db.models.user import User
from app.db.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.dependencies.auth_dep import auth_dep

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
def chat(
    chat_request: ChatRequest,
    current_user: Annotated[User, Depends(auth_dep)],
    db: Annotated[Session, Depends(get_db)],
) -> ChatResponse:

    return process_chat(chat_request.messages, current_user, db)
