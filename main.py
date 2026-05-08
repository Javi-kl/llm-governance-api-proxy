from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import get_db_context
from app.core.config import get_settings
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.core.bootstrap import bootstrap_admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    with get_db_context() as db:
        bootstrap_admin(db, settings.BOOTSTRAP_ADMIN_PASSWORD)
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
    ],  # Qué dominios pueden llamar a tu API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
