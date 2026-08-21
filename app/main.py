import logging
from contextlib import asynccontextmanager
from pathlib import Path

import gradio as gr
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core import config, bootstrap, exceptions, handlers, rate_limit, scheduler
from app.db.database import get_db_context
from app.dependencies.auth_dep import get_user_from_request
from app.routers import admin, auth, chat, health, web, models
from app.ui import gradio_chat, gradio_config


logger = logging.getLogger("main")

STATIC_DIR = Path(__file__).parent / "ui" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    with get_db_context() as db:
        bootstrap.bootstrap_admin(db, config.get_settings().BOOTSTRAP_ADMIN_PASSWORD)
    scheduler_var = scheduler.start_scheduler()
    try:
        yield
    finally:
        scheduler.stop_scheduler(scheduler_var)


app = FastAPI(lifespan=lifespan)

# ── Estáticos ────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── Exception handlers + rate limiting ──────────────────

handlers.register_exception_handlers(app)
rate_limit.setup_rate_limiting(app)

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

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/v1")
app.include_router(models.router, prefix="/v1")

# ── Páginas web ─────────────────────────────────────────

app.include_router(web.router)


# ── Gradio auth dependency ──────────────────────────────


def _gradio_auth(request: Request) -> str | None:
    with get_db_context() as db:
        try:
            user = get_user_from_request(request, db)
            return str(user.id)
        except exceptions.InvalidCredentialsError:
            # Caso esperado: usuario sin sesión válida — Gradio rechaza acceso.
            return None
        except Exception:
            logger.exception("Error inesperado validando sesión de Gradio")
            return None


# ── Gradio Chat UI ──────────────────────────────────────

gradio_app = gradio_chat.build_gradio_app()
app = gr.mount_gradio_app(
    app,
    gradio_app,
    path="/chat",
    auth_dependency=_gradio_auth,
    css=gradio_config.GRADIO_CSS,
    head=gradio_config.GRADIO_HEAD,
)
