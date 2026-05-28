import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.error_response import error_response
from app.db.database import get_db, ping
from app.schemas.error import ErrorEnvelope

logger = logging.getLogger("health")
router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        ping(db)
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error("Health check fallido: %s", e)
        return error_response(
            503,
            ErrorEnvelope(
                code="DATABASE_UNAVAILABLE",
                message="El servicio no está disponible en este momento",
            ),
        )
