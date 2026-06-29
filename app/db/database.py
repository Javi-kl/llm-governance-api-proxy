from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core import config

engine = create_engine(config.get_settings().DATABASE_URL, echo=False)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Abre una sesión por request; confirma al finalizar o revierte si hay excepción."""
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


def ping(db: Session) -> bool:
    db.execute(text("SELECT 1"))
    return True
