# Deuda Técnica

## TD-002: Formato de errores RF-8

- **Requisito**: RF-8 (formato envelope `{"error": {"code": ..., "message": ...}}`)
- **Estado**: Pendiente — cambio de contrato de API, rompería frontend y tests existentes
- **Archivos afectados**: `app/core/handlers.py`, todos los routers
- **Cerrar cuando**: antes del primer release, cuando se unifique el formato de errores
