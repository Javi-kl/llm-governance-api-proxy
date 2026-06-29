"""Helpers para setear y limpiar cookies de autenticación.

Extraídos del router de auth para que el router de páginas web
también pueda usarlos sin duplicar lógica de cookies.
"""

from datetime import timedelta

from fastapi.responses import Response

from app.core import config


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    settings = config.get_settings()

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=int(
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES).total_seconds()
        ),
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()),
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/api/v1/auth",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
