"""Rutas web de raíz y login.

El login web reutiliza auth_service.login() — la misma lógica que la API REST.
En vez de devolver JSON, responde con cookies + HX-Redirect (éxito)
o re-renderiza el formulario con error (fallo).
"""

import logging

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.cookies import set_auth_cookies
from app.core.enums import UserRole
from app.core.exceptions import InvalidCredentialsError
from app.core.rate_limit import limiter
from app.db.database import get_db
from app.dependencies.auth_dep import get_user_from_request
from app.repositories import users
from app.schemas.auth import LoginRequest
from app.services import auth
from app.routers.web.common import _redirect_for_user, _render_landing, _render_login

logger = logging.getLogger("pages")

router = APIRouter()


@router.get("/", response_model=None)
async def root(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Muestra la landing pública o redirige por rol si hay sesión activa."""
    if not request.cookies.get("access_token"):
        return _render_landing(request)

    try:
        user = get_user_from_request(request, db)
    except InvalidCredentialsError:
        return _render_landing(request)
    return _redirect_for_user(user)


@router.get("/login", response_class=HTMLResponse, response_model=None)
async def login_page(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Muestra el formulario de login; redirige por rol si ya hay sesión activa."""
    if not request.cookies.get("access_token"):
        return _render_login(request)

    try:
        user = get_user_from_request(request, db)
    except InvalidCredentialsError:
        return _render_login(request)
    return _redirect_for_user(user)


@router.post("/login")
@limiter.limit("5/5minute")
async def login_post(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """
    Éxito → HX-Redirect a /chat o /dashboard según rol + cookies de sesión.
    Fallo  → re-render del formulario con mensaje de error.
    """
    form = await request.form()
    username_value = form.get("username")
    username = username_value.strip() if isinstance(username_value, str) else ""
    credential_value = form.get("credential")
    credential = credential_value if isinstance(credential_value, str) else ""

    if not username or not credential:
        return _render_login(request, error="Usuario y credencial son obligatorios.")

    try:
        access_token, refresh_token = auth.login(
            LoginRequest(username=username, credential=credential),
            db,
        )
    except InvalidCredentialsError:
        return _render_login(request, error="Credenciales inválidas.")

    user = users.get_by_username(username, db)
    redirect_url = "/dashboard" if user and user.role == UserRole.ADMIN else "/chat"

    response = Response(status_code=200)
    response.headers["HX-Redirect"] = redirect_url
    set_auth_cookies(response, access_token, refresh_token)
    return response
