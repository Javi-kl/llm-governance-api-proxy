from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.bootstrap import bootstrap_admin
from app.core.config import get_settings
from app.core.exceptions import InvalidCredentialsError
from app.db.database import get_db_context
from app.routers.admin import router as admin_router
from app.routers.health import router as health_router
from app.routers.admin_auth import router as admin_auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    with get_db_context() as db:
        bootstrap_admin(db, settings.BOOTSTRAP_ADMIN_PASSWORD)
    yield


app = FastAPI(lifespan=lifespan)

# Si creo mas handlers, moverlos a un archivo en core/
@app.exception_handler(InvalidCredentialsError)
async def invalid_credentials_handler(request: Request, exc: InvalidCredentialsError):
    return JSONResponse(
        status_code=401,
        content={"detail": "Credenciales no válidas"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],  # Qué dominios pueden llamar a tu API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(admin_auth_router, prefix="/api/v1")
