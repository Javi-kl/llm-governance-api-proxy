from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AuditLog(Base):
    """
    Registro de auditoría por cada solicitud al proxy (RF-5).
    Almacena metadatos operativos — NUNCA el prompt ni la respuesta del LLM (RNF-3).
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    # UUID v4 generado en el servicio de chat
    request_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    # action ∈ {"allow", "mask", "block", "error"}
    # No se validan en BD — la fuente de verdad es el código (policy/provider/chat)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    detected_categories: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    # status {"success", "provider_error"}
    status: Mapped[str] = mapped_column(String(20), nullable=False)
