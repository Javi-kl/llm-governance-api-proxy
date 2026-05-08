# AGENTS.md — LLM Governance API Proxy

Guía de contexto para agentes de IA que trabajen en este proyecto.

---

## 1. Project Overview

| Aspecto | Valor |
|---------|-------|
| **Propósito** | Proxy API para centralizar y gobernar el uso de LLMs de terceros en pymes y autónomos |
| **Stack** | Python 3.12+, FastAPI 0.136, SQLAlchemy 2.0, PostgreSQL 16, Pydantic v2, Argon2id |
| **Auth** | JWT access + refresh tokens, roles `user` y `admin` |
| **Frontend** | Vanilla JS (separado del backend), se comunica por REST |
| **Deploy** | Docker Compose (proxy + PostgreSQL) |

---

## 2. Documentation Index

Lee estos archivos en orden cuando necesites entender el proyecto:

| Orden | Archivo | Qué contiene |
|-------|---------|--------------|
| 1 | `docs/overview.md` | Contexto, alcance del MVP, roadmap |
| 2 | `docs/architecture.md` | Patrón de capas, ADRs (decisiones arquitectónicas), flujo de requests, diagrama de despliegue |
| 3 | `docs/requirements.md` | RFs (requisitos funcionales), RNFs (no funcionales), RALs (requisitos de cumplimiento normativo) |
| 4 | `README.md` | Stack, arranque rápido, badges |

> **Nota**: `docs/changelog.md` está vacío actualmente.

---

## 3. Architecture Notes

### Patrón de capas

```
Router → Service → Repository
```

| Capa | Rol | Regla |
|------|-----|-------|
| **Router** | Recibe HTTP, valida entrada con Pydantic, delega | Solo HTTP y schemas |
| **Service** | Lógica de negocio, orquestación del flujo | Nunca toca HTTP ni BD directamente |
| **Repository** | Acceso a datos, queries SQLAlchemy | Nunca contiene lógica de negocio |

### Capas transversales

- **Schemas**: Modelos Pydantic de entrada/salida (contrato de la API)
- **Dependencies**: FastAPI `Depends()` — inyectan usuario autenticado, sesión BD, permisos
- **Core**: Config (.env), seguridad (Argon2id, JWT), excepciones HTTP, rate limit, scheduler
- **DB**: Conexión, modelos SQLAlchemy, migraciones

### Flujo de una request de chat

```
Cliente → Middleware (Auth + Rate) → Detector (regex) → Policy (block/mask/allow)
  → Provider (reenvía a LLM) → Logger (guarda metadatos) → Respuesta JSON
```

---

## 4. Development Commands

```bash
# Levantar con Docker Compose (recomendado)
docker compose up

# Levantar solo el backend (requiere PostgreSQL corriendo)
uvicorn main:app --reload

# Tests
pytest

# Acceso a la API
# Swagger UI: http://localhost:8000/docs
```

---

## 5. Code Conventions

### Language Policy (obligatorio)

| Contexto | Idioma | Ejemplo |
|----------|--------|---------|
| Variables, funciones, clases, archivos, tipos | **Inglés** | `get_user`, `AuthService`, `user.py` |
| Comentarios, docstrings, logs, mensajes de error, UI/CLI strings | **Español** | `# Obtiene el usuario activo` |
| Commits | Conventional commits (`feat:`, `fix:`) — descripción en español | `feat: agrega detector de IBAN` |

### SQLAlchemy 2.0

Usar el estilo moderno. **NO** usar `Column` de SQLA 1.x.

```python
# ✅ CORRECTO
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
```

### Pydantic v2

```python
# ✅ CORRECTO
from pydantic import BaseModel, ConfigDict

class UserCreate(BaseModel):
    model_config = ConfigDict(strict=True)
    username: str
    role: str
```

### Type Hints

Obligatorios en funciones públicas. Usar `typing` cuando sea necesario.

```python
# ✅ CORRECTO
from typing import Optional

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    ...
```

### Error Handling

- Nunca silenciar errores (`except: pass` está prohibido)
- Usar excepciones específicas
- En producción, no exponer stacks ni detalles internos al cliente

---

## 6. Key Domain Rules

Estas reglas son críticas y están documentadas en detalle en `docs/requirements.md`:

| Regla | Descripción | Referencia |
|-------|-------------|------------|
| **NO persistir prompts ni respuestas** | Los logs de auditoría guardan metadatos, NUNCA el contenido del prompt o la respuesta | RNF-3, RF-5 |
| **Detección por regex** | El detector usa regex puro (módulo `re`). NO usar ML ni heurísticas en el MVP | ADR-8, RF-2 |
| **Bootstrap admin por env var** | El primer admin se crea al arrancar via `BOOTSTRAP_ADMIN_PASSWORD`. NO existe endpoint de registro público | RF-13 |
| **Retención 90 días** | Los logs de auditoría se eliminan automáticamente a los 90 días (APScheduler) | RAL-2, ADR-9 |
| **Política de prioridad** | Si un prompt dispara varias categorías: `block > mask > allow` | RF-3 |
| **Rate limit en login** | Tras 5 fallos consecutivos, la IP se bloquea 15 min. Un login exitoso resetea el contador | RF-16 |
| **Secrets por env vars** | Ningún secreto en código fuente. Todo por variables de entorno | RNF-9 |

---

## 7. Testing

```bash
# Correr todos los tests
pytest

# Correr un test específico
pytest tests/test_auth.py -v

# Con coverage
pytest --cov=app --cov-report=term-missing
```

- Estructura `tests/` debe reflejar `app/`
- Tests unitarios: sin llamadas a red
- Tests de integración: con BD de test (fixture)

---

## 8. Security Rules

- **Secrets**: Solo por variables de entorno (`.env`). Nunca hardcodeados.
- **JWT**: En cookies `HttpOnly` (1h de duración). Refresh token en BD.
- **Password hashing**: Argon2id (configuración en `app/core/security.py`)
- **CORS**: Habilitado solo en desarrollo (`localhost:3000`, `localhost:5173`)
- **Rate limiting**: SlowAPI general + lógica propia para login (PostgreSQL)

---

## 9. Project Structure

```text
app/
├── core/           # Config, seguridad, excepciones, rate limit, scheduler
├── db/             # Engine, SessionLocal, modelos SQLAlchemy
├── dependencies/   # FastAPI Depends (auth_deps, db deps)
├── repositories/   # Acceso a datos (user_repo, audit_repo, session_repo)
├── routers/        # Endpoints HTTP (auth, chat, admin, health)
├── schemas/        # Pydantic models (auth, chat, admin, error)
├── services/       # Lógica de negocio (auth, detector, policy, provider, chat, audit)
docs/               # Documentación del proyecto
frontend/           # UI vanilla (HTML/CSS/JS) — separada del backend
tests/              # Tests con pytest
```

---

## 10. When in Doubt

1. Revisa `docs/architecture.md` para decisiones arquitectónicas
2. Revisa `docs/requirements.md` para criterios de aceptación
3. Revisa `docs/requirements.md` → sección "Mapeo normativo" para cumplimiento GDPR/AI Act
4. Consulta los ADRs en `docs/architecture.md` antes de cambiar un patrón fundamental
5. **Nunca asumas**: si algo no está claro, pregunta antes de implementar
