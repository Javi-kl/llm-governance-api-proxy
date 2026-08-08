import pytest
from pydantic import ValidationError

from app.core.enums import MessageRole
from app.schemas.chat import (
    MAX_MESSAGES_LENGTH,
    ChatCompletionRequest,
    ChatResponse,
    MAX_CONTENT_LENGTH,
    MessageItem,
)


def test_given_one_user_message_then_creates_chat_request():
    req = ChatCompletionRequest(
        model="test-model",
        messages=[MessageItem(role=MessageRole.USER, content="Hola")],
    )

    assert len(req.messages) == 1
    assert req.messages[0].role == MessageRole.USER
    assert req.messages[0].content == "Hola"


@pytest.mark.parametrize(
    "messages",
    [
        [],
        [MessageItem(role=MessageRole.ASSISTANT, content="Hola")],
        [MessageItem(role=MessageRole.SYSTEM, content="Be brief")],
    ],
    ids=["empty", "only_assistant", "only_system"],
)
def test_given_no_user_message_then_raises_validation_error(messages):
    with pytest.raises(ValidationError, match="user"):
        ChatCompletionRequest(model="model-test", messages=messages)


def test_given_invalid_role_then_raises_validation_error():
    with pytest.raises(ValidationError):
        MessageItem.model_validate({"role": "moderator", "content": "X"})


def test_given_extra_field_then_ignores_it():
    request = ChatCompletionRequest.model_validate(
        {
            "model": "test-model",
            "messages": [{"role": "user", "content": " Hola"}],
            "temperature": 0.7,
        }
    )

    assert request.model == "test-model"
    assert "temperature" not in request.model_dump()


def test_given_invalid_action_then_raises_validation_error():
    with pytest.raises(ValidationError):
        ChatResponse.model_validate(
            {
                "request_id": "abc-123",
                "action": "unknown",
                "message": None,
                "detected_categories": [],
                "reason": None,
            }
        )


def test_given_too_long_message_content_then_raises_validation_error():
    content = "x" * (MAX_CONTENT_LENGTH + 1)

    with pytest.raises(ValidationError, match="caracteres"):
        MessageItem(role=MessageRole.USER, content=content)


def test_given_too_many_messages_then_raises_validation_error():
    messages = [
        MessageItem(role=MessageRole.USER, content="Hola")
        for _ in range(MAX_MESSAGES_LENGTH + 1)
    ]
    with pytest.raises(ValidationError, match="limite"):
        ChatCompletionRequest(
            model="test-model",
            messages=messages,
        )


def test_given_stream_true_then_raises_validation_error():
    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate(
            {
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hola"}],
                "stream": True,
            }
        )
