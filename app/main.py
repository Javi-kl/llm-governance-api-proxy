import logging
from contextlib import asynccontextmanager
from pathlib import Path

import gradio as gr
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core import config
from app.core.bootstrap import bootstrap_admin
from app.core.exceptions import InvalidCredentialsError
from app.core.handlers import register_exception_handlers
from app.core.rate_limit import setup_rate_limiting
from app.db.database import get_db_context
from app.dependencies.auth_dep import get_user_from_request
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.health import router as health_router
from app.routers.web import router as pages_router
from app.ui.gradio_chat import build_gradio_app

logger = logging.getLogger("main")

STATIC_DIR = Path(__file__).parent / "ui" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    with get_db_context() as db:
        bootstrap_admin(db, config.get_settings().BOOTSTRAP_ADMIN_PASSWORD)
    yield


app = FastAPI(lifespan=lifespan)

# ── Estáticos ────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── Exception handlers + rate limiting ──────────────────

register_exception_handlers(app)
setup_rate_limiting(app)

# ── CORS ────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ─────────────────────────────────────────

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")

# ── Páginas web ─────────────────────────────────────────

app.include_router(pages_router)


# ── Gradio auth dependency ──────────────────────────────


def _gradio_auth(request: Request) -> str | None:
    with get_db_context() as db:
        try:
            user = get_user_from_request(request, db)
            return str(user.id)
        except InvalidCredentialsError:
            # Caso esperado: usuario sin sesión válida — Gradio rechaza acceso.
            return None
        except Exception:
            logger.exception("Error inesperado validando sesión de Gradio")
            return None


# ── Gradio Chat UI ──────────────────────────────────────

gradio_app = build_gradio_app()
app = gr.mount_gradio_app(
    app,
    gradio_app,
    path="/chat",
    auth_dependency=_gradio_auth,
)
