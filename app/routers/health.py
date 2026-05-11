from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db, ping

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        ping(db)
        return {"status": "healthy", "database": "connected"}
    except Exception:
        raise HTTPException(
            status_code=503, detail={"status": "unhealthy", "database": "disconnected"}
        )
