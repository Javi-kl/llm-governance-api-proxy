## Contexto

Las empresas europeas usan cada vez más LLMs. Pero los empleados pueden introducir sin querer datos personales de clientes, compañeros o proveedores en los prompts. GDPR y AI Act exigen control sobre esos datos.
Este proxy se sitúa entre el usuario y el LLM para inspeccionar, enmascarar o bloquear información sensible antes de que salga de la empresa.

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

- Proxy API con endpoint `/api/v1/chat` (multi-turn, contrato propio).
- Detección por regex de 3 categorías: identificación, contacto, financiero
- Política por categoría (mask/block) definida en código
- Autenticación: PIN para usuarios, contraseña para admins
- Bootstrap del primer admin al desplegar
- Gestión de usuarios normales vía API de administración (crear, desactivar, resetear PIN). Un único admin;
- Logs de auditoría sin prompts ni respuestas, retención de 90 días
- Health check, rate limit en login, errores controlados
- Despliegue con Docker Compose
- UI de chat demo con gradio renderizada desde el backend con htmx y jinja.


## Fuera de alcance

- Multi-tenant ni multiempresa
- SSO, MFA, RBAC complejo
- Procesado documental completo
- SDK propio ni integraciones externas
- Contador de tokens (pospuesto)
- Panel de estadísticas visuales avanzadas

## Roadmap

### MVP
- [X] Proxy API funcional con endpoint /api/v1/chat
- [X] Detección regex de 3 categorías (identificación, contacto, financiero)
- [X] Política mask/block por categoría
- [X] Autenticación (PIN user, password admin)
- [X] Bootstrap del primer admin
- [X] Gestión de usuarios normales vía API de administración (rol user únicamente)
- [X] Logs de auditoría (sin prompts/respuestas, retención 90 días)
- [X] Health check y rate limit en login
- [X] Login web único en /login (Jinja2 + HTMX)
- [X] Redirección automática por rol tras login (user → /chat, admin → /dashboard)
- [X] Chat demo Gradio en /chat (demo temporal)
- [X] Dashboard admin con enlaces a herramientas administrativas (Jinja2 + HTMX)
- [X] Docker Compose + .env.example

### Beta
- [ ] Informe de cumplimiento (pospuesto desde MVP — RF-19)
- [ ] Migrar detector a Presidio
- [ ] Compatibilidad OpenAI API (Prioridad)
- [ ] Detectar prompt injection

---

## Esqueleto

```text
app/
├── main.py                 ← Crea la app, registra routers, estáticos, Gradio y scheduler
├── core/                   ← Configuración, seguridad, errores, cookies, rate limit y proveedor LLM
│   ├── config.py
│   ├── security.py
│   ├── provider.py
│   ├── scheduler.py
│   └── ...
├── db/
│   ├── database.py         ← Engine, SessionLocal, Base y helpers de sesión
│   └── models/
│       ├── user.py         ← Usuario, rol y credenciales hasheadas
│       ├── refresh_token.py ← Refresh tokens persistidos
│       └── audit_log.py    ← Metadatos de auditoría
├── dependencies/
│   └── auth_dep.py         ← Dependencias de autenticación y permisos
├── repositories/
│   ├── users.py            ← Acceso a datos de usuarios
│   ├── refresh_tokens.py   ← Acceso a datos de sesiones
│   └── audit_logs.py       ← Acceso a datos de auditoría
├── schemas/
│   ├── auth.py             ← Schemas de autenticación
│   ├── chat.py             ← Schemas del endpoint de chat
│   ├── admin.py            ← Schemas de administración y auditoría
│   ├── user.py             ← Schemas de usuario
│   └── error.py            ← Schemas de error
├── services/
│   ├── auth.py             ← Login, logout, refresh y cookies
│   ├── admin.py            ← Gestión de usuarios
│   ├── chat.py             ← Orquestación detector → policy → provider → audit
│   ├── detector.py         ← Detección regex de datos sensibles
│   ├── policy.py           ← Decisión allow/mask/block
│   ├── audit.py            ← Creación y consulta de logs
│   └── scheduler.py        ← Limpieza de retención
├── routers/
│   ├── auth.py             ← Endpoints /api/v1/auth/*
│   ├── chat.py             ← Endpoint /api/v1/chat
│   ├── admin.py            ← Endpoints /api/v1/admin/*
│   ├── health.py           ← Endpoint /api/v1/health
│   └── web/
│       ├── login.py        ← Página de login
│       ├── dashboard.py    ← Panel principal de admin
│       ├── users.py        ← Gestión web de usuarios
│       ├── audit_logs.py   ← Consulta web de logs
│       └── common.py       ← Helpers comunes de rutas web
└── ui/
    ├── gradio_chat.py      ← Chat demo montado en /chat
    ├── templates.py        ← Configuración de Jinja2
    ├── templates/          ← Plantillas HTML
    └── static/             ← CSS y recursos estáticos

tests/
├── core/
├── dependencies/
├── repositories/
├── routers/
├── schemas/
├── services/
├── ui/
└── conftest.py

scripts/
├── entrypoint.sh           ← Migraciones + arranque uvicorn
└── init-test-db.sh         ← Inicialización de base de datos de test

.env.example
docker-compose.yml          ← App + PostgreSQL para ejecución local
```
