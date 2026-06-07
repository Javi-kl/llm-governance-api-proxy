## Contexto

Las pymes y autónomos europeos usan cada vez más LLMs (ChatGPT, Claude, etc.). Pero los empleados pueden introducir sin querer datos personales de clientes, compañeros o proveedores en los prompts. GDPR y AI Act exigen control sobre esos datos. Este proxy se sitúa entre el usuario y el LLM para inspeccionar, enmascarar o bloquear información sensible antes de que salga de la empresa.

## Objetivo del MVP

Un proxy local que:

- Recibe prompts de usuarios autenticados y los reenvía al LLM
- Detecta datos sensibles antes de enviarlos (DNI, email, IBAN, etc.)
- Aplica políticas automáticas: enmascara o bloquea según la categoría
- Registra metadatos de cada solicitud para auditoría (sin guardar el contenido)
- Ofrece una UI web ligera para login y chat demo, API REST para administración, y documentación Swagger

## Casos de uso cubiertos

| Caso de uso | Descripción | Riesgo controlado |
|---|---|---|
| Chatbot de atención al cliente | El cliente pega datos personales en el chat | Detección + enmascarado/bloqueo automático |
| Asistente interno para empleados | Un empleado incluye datos de compañeros o nóminas | Detección + enmascarado/bloqueo automático |

## Alcance del MVP

- Proxy API con endpoint `/api/v1/chat` (multi-turn, contrato propio). El endpoint compatible OpenAI queda en Beta
- Detección por regex de 3 categorías: identificación, contacto, financiero
- Política por categoría (mask/block) definida en código
- Autenticación: PIN para usuarios, contraseña para admins
- Bootstrap del primer admin al desplegar
- Gestión de usuarios normales vía API de administración (crear, desactivar, resetear PIN). Un único admin; no se crean admins adicionales desde la interfaz.
- Logs de auditoría sin prompts ni respuestas, retención de 90 días
- Health check, rate limit en login, errores controlados
- Informe de cumplimiento descargable para auditorías
- Despliegue con Docker Compose

## Fuera de alcance

- Multi-tenant ni multiempresa
- SSO, MFA, RBAC complejo
- Procesado documental completo
- SDK propio ni integraciones externas
- Contador de tokens (pospuesto)
- Panel de estadísticas visuales avanzadas

## Roadmap

### MVP
- [ ] Proxy API funcional con endpoint /api/v1/chat
- [ ] Detección regex de 3 categorías (identificación, contacto, financiero)
- [ ] Política mask/block por categoría
- [X] Autenticación (PIN user, password admin)
- [X] Bootstrap del primer admin
- [X] Gestión de usuarios normales vía API de administración (rol user únicamente)
- [ ] Logs de auditoría (sin prompts/respuestas, retención 90 días)
- [X] Health check y rate limit en login
- [ ] Informe de cumplimiento
- [X] Login web único en /login (Jinja2 + HTMX)
- [ ] Redirección automática por rol tras login (user → /chat, admin → /dashboard)
- [X] Chat demo Gradio en /chat (demo temporal)
- [ ] Dashboard admin con enlaces a herramientas administrativas (Jinja2 + HTMX)
- [ ] Docker Compose + .env.example

### Beta
- [ ] Migrar detector a Presidio
- [ ] Más categorías (salud, legal)
- [ ] Compatibilidad OpenAI API para integrar con Open WebUI

### Producto
- [ ] Multi-proveedor
- [ ] Panel de estadísticas
- [ ] Nginx en producción
- [ ] Tests de carga

---

## Esqueleto

```text
app/ui/
├── __init__.py          ← Inicializa el módulo de UI
├── gradio_chat.py       ← Chat demo temporal con Gradio, montado en /chat
├── templates.py         ← Configuración de Jinja2 (directorio de templates)
├── templates/
│   ├── base.html        ← Layout base HTML
│   └── login.html       ← Página de login web (formulario HTMX)
└── static/
    └── style.css        ← Estilos globales

app/
├── main.py              ← Crea la app, registra routers, arranca APScheduler
├── core/
│   ├── config.py        ← Settings con pydantic-settings (lee .env)
│   ├── security.py      ← Argon2id, firma/verificación JWT
│   ├── exceptions.py    ← Errores HTTP controlados (RF-8)
│   ├── scheduler.py     ← APScheduler: limpieza de retención (ADR-9)
│   └── rate_limit.py    ← Rate limiting con SlowAPI (RF-16)
├── db/
│   ├── database.py      ← Engine, SessionLocal, Base, get_db
│   └── models/
│       ├── user.py       ← User (username, pin_hash/password_hash, role, active)
│       ├── session.py    ← RefreshToken (user_id, token_hash, expires_at)
│       └── audit_log.py  ← AuditLog (request_id, timestamp, user_id, action...)
├── dependencies/
│   └── auth_deps.py     ← get_current_user: extrae JWT de cookie, retorna User
├── repositories/
│   ├── user_repo.py     ← create, get_by_username, get_by_id, update, deactivate
│   ├── session_repo.py  ← create, get, delete, delete_by_user_id
│   └── audit_repo.py    ← create, list (con filtros y paginación)
├── schemas/
│   ├── auth.py          ← LoginRequest, UserCreate, UserResponse
│   ├── chat.py          ← ChatRequest, ChatResponse
│   ├── admin.py         ← UserManagement, AuditLogFilter, ComplianceReport
│   └── error.py         ← ErrorResponse (code, message, details)
├── services/
│   ├── auth_service.py  ← login, logout, refresh, create_user, reset_pin
│   ├── detector.py      ← Escanea prompt con regex (ADR-8)
│   ├── policy.py        ← Decide acción por categoría (ADR-3)
│   ├── provider.py      ← Reenvía al LLM externo (ADR-7)
│   ├── chat_service.py  ← Orquestador: detector → policy → provider → logger
│   ├── audit_service.py ← Guarda logs, consulta con filtros, genera informe (RF-19)
│   └── scheduler_service.py ← Lógica SQL de limpieza de retención
├── routers/
│   ├── auth_router.py   ← /api/v1/auth/*
│   ├── chat_router.py   ← /api/v1/chat
│   ├── admin_router.py  ← /api/v1/admin/*
│   └── health_router.py ← /api/v1/health
└── templates/           ← (carpeta vacía — las plantillas web están en app/ui/templates/)

tests/
├── conftest.py
├── test_auth.py
├── test_chat.py
├── test_detector.py
├── test_policy.py
├── test_admin.py
└── test_health.py

scripts/
└── entrypoint.sh        ← Migraciones + arranque uvicorn

.env.example
docker-compose.yml       ← PostgreSQL local de desarrollo
```
