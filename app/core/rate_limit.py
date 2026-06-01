import logging

from fastapi import Request, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.error_response import error_response
from app.schemas.error import ErrorEnvelope

logger = logging.getLogger("rate_limit")


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    logger.warning(
        "Rate limit superado - IP: %s, Path: %s",
        request.client.host if request.client else "unknown",
        request.url.path,
    )
    response = error_response(
        429,
        ErrorEnvelope(
            code="RATE_LIMIT_EXCEEDED",
            message="Demasiadas solicitudes. Inténtalo de nuevo más tarde.",
        ),
    )
    response = request.app.state.limiter._inject_headers(
        response, request.state.view_rate_limit
    )
    return response


limiter: Limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    swallow_errors=True,
)


def setup_rate_limiting(app) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
