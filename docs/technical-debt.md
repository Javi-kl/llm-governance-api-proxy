# Deuda Técnica

## TD-001: Invalidar sesiones al desactivar/resetear PIN

- **Requisito**: RF-17 (criterios de aceptación líneas 189, 191)
- **Estado**: Bloqueado — no existe modelo ni repositorio de sesiones
- **Archivos afectados**: `app/services/admin.py` (`deactivate_user`, `reset_user_pin`)
- **Cerrar cuando**: se implemente `session_repo` y el modelo `Session`/`RefreshToken`

## TD-002: Formato de errores RF-8

- **Requisito**: RF-8 (formato envelope `{"error": {"code": ..., "message": ...}}`)
- **Estado**: Pendiente — cambio de contrato de API, rompería frontend y tests existentes
- **Archivos afectados**: `app/core/handlers.py`, todos los routers
- **Cerrar cuando**: antes del primer release, cuando se unifique el formato de errores
