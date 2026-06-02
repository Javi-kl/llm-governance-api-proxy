"""Orquestador del endpoint POST /api/v1/chat.
Coordina detector, policy, provider y audit para procesar el array de mensajes
del usuario y devolver una respuesta estructurada sin persistir contenido (RNF-3).
"""

import time
import uuid
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from app.core import exceptions
from app.core.config import get_settings
from app.core.enums import MessageRole, PolicyAction, SensitiveCategory
from app.core.provider import send as provider_send
from app.db.models.user import User
from app.schemas.chat import ChatResponse, MessageItem
from app.services import audit, detector, policy


def process_chat(
    messages: list[MessageItem],
    user: User,
    db: Session,
) -> ChatResponse:
    request_id = str(uuid.uuid4())
    settings = get_settings()
    start = time.monotonic()

    sanitized, detected_categories = _redetect_and_sanitize(messages)
    action = policy.evaluate(list(detected_categories))
    detected_str = [c.value for c in detected_categories]
    latency_ms = int((time.monotonic() - start) * 1000)
    provider_host = urlparse(str(settings.LLM_BASE_URL)).hostname or "unknown"

    audit_ctx = {
        "request_id": request_id,
        "user_id": user.id,
        "provider": provider_host,
        "model": settings.LLM_MODEL,
        "db": db,
    }

    if action == PolicyAction.BLOCK:
        return _build_block_response(audit_ctx, detected_str, latency_ms)

    if action == PolicyAction.MASK:
        sanitized.insert(
            0,
            MessageItem(
                role=MessageRole.SYSTEM,
                content=policy.PRIVACY_SYSTEM_PROMPT,
            ),
        )

    messages_dicts = [m.model_dump() for m in sanitized]
    text = _call_provider_and_audit(
        audit_ctx,
        action.value,
        detected_str,
        latency_ms,
        messages_dicts,
    )
    return ChatResponse(
        request_id=request_id,
        action=action.value,
        message=MessageItem(role=MessageRole.ASSISTANT, content=text),
        detected_categories=detected_str,
        reason=None,
    )


def _redetect_and_sanitize(
    messages: list[MessageItem],
) -> tuple[list[MessageItem], set[SensitiveCategory]]:
    sanitized: list[MessageItem] = []
    detected_categories: set[SensitiveCategory] = set()
    for msg in messages:
        if msg.role != MessageRole.USER:
            sanitized.append(msg)
            continue
        detections = detector.analyze(msg.content)
        if not detections:
            sanitized.append(msg)
            continue
        detected_categories.update(d.category for d in detections)
        sanitized.append(
            MessageItem(
                role=msg.role,
                content=policy.mask_values(msg.content, detections),
            )
        )
    return sanitized, detected_categories


def _build_block_response(
    audit_ctx: dict,
    detected_str: list[str],
    latency_ms: int,
) -> ChatResponse:
    reason = f"Contenido sensible detectado: {', '.join(detected_str)}"
    audit.register_log(
        **audit_ctx,
        action="block",
        detected_categories=detected_str,
        latency_ms=latency_ms,
        status="success",
    )
    return ChatResponse(
        request_id=audit_ctx["request_id"],
        action="block",
        message=None,
        detected_categories=detected_str,
        reason=reason,
    )


def _call_provider_and_audit(
    audit_ctx: dict,
    action: str,
    detected_str: list[str],
    latency_ms: int,
    messages_dicts: list[dict[str, str]],
) -> str:
    try:
        text = provider_send(messages_dicts)
    except (exceptions.ProviderError, exceptions.ProviderTimeoutError):
        audit.register_log(
            **audit_ctx,
            action="error",
            detected_categories=detected_str,
            latency_ms=latency_ms,
            status="provider_error",
        )
        raise
    audit.register_log(
        **audit_ctx,
        action=action,
        detected_categories=detected_str,
        latency_ms=latency_ms,
        status="success",
    )
    return text
