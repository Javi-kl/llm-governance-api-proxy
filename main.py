from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    from zxcvbn import zxcvbn
    zxcvbn("warmup")
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
    ],  # Qué dominios pueden llamar a tu API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
