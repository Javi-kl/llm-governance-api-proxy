from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.DATABASE_URL, echo=False)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Sesión para Depends() en rutas."""
    db: Session = SessionLocal()
    try:
        yield db  # ← ruta inserta, actualiza..
        db.commit()  # ← aquí llega TODO a disco (o nada)
    except Exception:
        db.rollback()  # ← algo falló → deshacer todo
        raise  # ← la excepción sigue subiendo
    finally:
        db.close()

# Wrapper para usar con 'with' en lifespan, scripts, tareas..
get_db_context = contextmanager(get_db)