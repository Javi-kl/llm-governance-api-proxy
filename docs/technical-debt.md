# Deuda Técnica

## TD-002: Formato de errores RF-8 -> **CERRADO**

- **Requisito**: RF-8 (formato envelope `{"error": {"code": ..., "message": ...}}`)
- **Estado**: Cerrado — el formato de errores ya está unificado
- **Archivos afectados**: `app/core/handlers.py`, `app/core/error_response.py`, `app/schemas/error.py`
- **Cerrado cuando**: se centralizó el envelope de errores para validación, autenticación, permisos, proveedor y errores internos

---

## TD-003: Gradio no implementa auto-refresh del access token

- **Requisito**: RF-14 (sesiones), RNF-4 (usabilidad)
- **Estado**: Pendiente
- **Archivos afectados**: `app/ui/gradio_chat.py`, `app/main.py` (auth_dependency de Gradio)
- **Impacto**: Si el access token expira durante una sesión de chat en Gradio, el usuario ve un error y debe reautenticarse manualmente. El refresh token no es legible desde JavaScript porque va en cookie HttpOnly; renovar la sesión requiere que el cliente llame explícitamente a `/api/v1/auth/refresh`, y Gradio no integra ese flujo de forma transparente.
- **Motivo**: Gradio se mantiene como chat demo temporal (ADR-1). Invertir en un mecanismo de auto-refresh para Gradio no tiene retorno si la UI se migra a OpenWebUI u otra alternativa en Beta.
- **Cierre futuro**: Al reemplazar Gradio:
  - Si se usa OpenWebUI: delegar la renovación al propio OpenWebUI (soporta OAuth y refresh nativo).
  - Si se construye una UI propia: implementar un interceptor fetch que, ante 401, llame a `/api/v1/auth/refresh` y reintente la petición original.
- **Mitigación actual**: El access token tiene 1 hora de vida (ADR-5), suficiente para sesiones de demostración. Si caduca durante el uso de Gradio, el usuario debe volver a iniciar sesión o usar un cliente que llame explícitamente a `/api/v1/auth/refresh`.
