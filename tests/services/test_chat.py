from unittest.mock import patch

import pytest

from app.core.enums import MessageRole
from app.core.exceptions import ProviderTimeoutError
from app.db.models.audit_log import AuditLog
from app.db.models.user import User
from app.schemas.chat import MessageItem
from app.services import chat
from app.services.policy import PRIVACY_SYSTEM_PROMPT


def _user_message(content: str) -> MessageItem:
    return MessageItem(role=MessageRole.USER, content=content)


def test_given_no_sensitive_data_then_returns_allow_and_audits_success(
    db_session, regular_user: User
):
    messages = [_user_message("¿Capital de Francia?")]

    with patch("app.services.chat.provider_send", return_value="París") as mock:
        response = chat.process_chat(messages, regular_user, db_session)

    assert response.action == "allow"
    assert response.message is not None
    assert response.message.content == "París"
    assert response.detected_categories == []
    assert response.reason is None
    assert len(response.request_id) == 36

    mock.assert_called_once()
    sent = mock.call_args.args[0]
    assert sent == [{"role": "user", "content": "¿Capital de Francia?"}]

    log = db_session.query(AuditLog).filter_by(request_id=response.request_id).one()
    assert log.user_id == regular_user.id
    assert log.action == "allow"
    assert log.status == "success"


def test_given_email_in_user_then_masks_injects_system_and_audits_mask(
    db_session, regular_user: User
):
    messages = [_user_message("Escribe a j@x.com por favor")]

    with patch("app.services.chat.provider_send", return_value="OK") as mock:
        response = chat.process_chat(messages, regular_user, db_session)

    assert response.action == "mask"
    assert response.message is not None
    assert response.detected_categories == ["contacto"]

    sent = mock.call_args.args[0]
    assert sent[0] == {"role": "system", "content": PRIVACY_SYSTEM_PROMPT}
    assert sent[1] == {"role": "user", "content": "Escribe a [EMAIL] por favor"}

    log = db_session.query(AuditLog).filter_by(request_id=response.request_id).one()
    assert log.action == "mask"
    assert log.status == "success"


def test_given_iban_in_user_then_blocks_without_calling_provider(
    db_session, regular_user: User
):
    messages = [_user_message("Mi cuenta es ES9121000418450200051332")]

    with patch("app.services.chat.provider_send") as mock:
        response = chat.process_chat(messages, regular_user, db_session)

    mock.assert_not_called()
    assert response.action == "block"
    assert response.message is None
    assert response.detected_categories == ["financiero"]
    assert response.reason is not None and "financiero" in response.reason

    log = db_session.query(AuditLog).filter_by(request_id=response.request_id).one()
    assert log.action == "block"
    assert log.status == "success"


def test_given_assistant_message_with_email_then_does_not_mask_it(
    db_session, regular_user: User
):
    messages = [
        _user_message("Hola"),
        MessageItem(
            role=MessageRole.ASSISTANT,
            content="Tu email j@x.com está registrado",
        ),
    ]

    with patch("app.services.chat.provider_send", return_value="OK") as mock:
        chat.process_chat(messages, regular_user, db_session)

    sent = mock.call_args.args[0]
    assert sent == [
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "Tu email j@x.com está registrado"},
    ]


def test_given_provider_timeout_then_audits_error_and_raises(
    db_session, regular_user: User
):
    messages = [_user_message("Hola")]

    with patch(
        "app.services.chat.provider_send",
        side_effect=ProviderTimeoutError(),
    ):
        with pytest.raises(ProviderTimeoutError):
            chat.process_chat(messages, regular_user, db_session)

    log = (
        db_session.query(AuditLog)
        .filter_by(user_id=regular_user.id)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert log.action == "error"
    assert log.status == "provider_error"
