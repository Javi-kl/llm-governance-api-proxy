"""Rutas de páginas web del proxy: raíz y login.

El login web reutiliza auth_service.login() — la misma lógica que la API REST.
En vez de devolver JSON, responde con cookies + HX-Redirect (éxito)
o re-renderiza el formulario con error (fallo).
"""

import logging

import jwt
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.core import config
from app.core.cookies import set_auth_cookies
from app.core.exceptions import InvalidCredentialsError
from app.db.database import get_db
from app.schemas.auth import LoginRequest
from app.services import auth
from app.ui.templates import templates

logger = logging.getLogger("pages")

router = APIRouter()


@router.get("/")
async def root(request: Request) -> RedirectResponse:
    """Redirige a /chat si hay sesión activa, a /login en caso contrario.

    Solo valida firma y expiración del JWT, sin consultar BD.
    La validación completa ocurre en el auth_dependency de Gradio en /chat.
    """
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=302)

    settings = config.get_settings()
    try:
        jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM],
        )
        return RedirectResponse(url="/chat", status_code=302)
    except InvalidTokenError:
        return RedirectResponse(url="/login", status_code=302)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    """Muestra el formulario de inicio de sesión."""
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request},
    )


@router.post("/login")
async def login_post(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Procesa el login vía formulario web (HTMX).

    Éxito → HX-Redirect a /chat + cookies de sesión.
    Fallo  → re-render del formulario con mensaje de error.
    """
    form = await request.form()
    username_value = form.get("username")
    username = username_value.strip() if isinstance(username_value, str) else ""
    credential_value = form.get("credential")
    credential = credential_value if isinstance(credential_value, str) else ""

    if not username or not credential:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "request": request,
                "error": "Usuario y credencial son obligatorios.",
            },
        )

    try:
        access_token, refresh_token = auth.login(
            LoginRequest(username=username, credential=credential),
            db,
        )
    except InvalidCredentialsError:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "request": request,
                "error": "Credenciales inválidas.",
            },
        )

    response = Response(status_code=200)
    response.headers["HX-Redirect"] = "/chat"
    set_auth_cookies(response, access_token, refresh_token)
    return response
