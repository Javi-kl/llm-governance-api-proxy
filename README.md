# llm-governance-api-proxy
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-AGPL%203.0-green.svg)](LICENSE)

> Este proyecto implementa una API proxy para centralizar y controlar el uso de modelos LLM de terceros en pymes y autónomos.
Antes de reenviar cada solicitud al proveedor externo, inspecciona el texto para detectar categorías sensibles, aplica una política de: Block/Mask/Allow, y genera trazabilidad mínima útil para auditoría sin almacenar por defecto el contenido completo de prompts y respuestas.
El MVP se acompaña de una UI web local sencilla y de una API documentada con Swagger para demostrar su funcionamiento e integración.

> Documentación: [`architecture.md`](./docs/architecture.md) · [`overview.md`](./docs/overview.md) · [`requirements.md`](./docs/requirements.md)

---
## Casos de uso en MVP

| Caso de uso | Valor | Riesgo a controlar |
| ---- | ---- | ---- |
| **Chatbot de atención al cliente** | *Reduce carga del equipo, evita envío accidental de datos sensibles y mantiene un servicio de atención más estable.* | *El cliente puede pegar datos personales, números de pedido o incidencias con información sensible.* |
| **Asistente interno para empleados** | *Ahorra tiempo al equipo y evita que se usen datos sensibles sin control.* | *Un empleado puede incluir datos de compañeros, clientes, nóminas o incidencias internas.* |

## Funcionalidades principales
- Autenticación con admin y usuarios.
- Chat proxy hacia proveedor LLM.
- Detección de datos sensibles.
- Política allow/mask/block.
- Auditoría sin almacenar prompts ni respuestas.
- Panel admin para gestionar usuarios y logs.
- Ejecución con Docker Compose.

## Estructura del proyecto

El proyecto sigue una arquitectura por capas `Router → Service → Repository`.

```text
app/
├── core/           # Configuración, seguridad, excepciones, proveedor LLM y scheduler
├── db/             # Conexión a PostgreSQL y modelos SQLAlchemy
├── dependencies/   # Dependencias de FastAPI para auth y permisos
├── repositories/   # Acceso a datos
├── routers/        # Endpoints REST
├── schemas/        # Modelos Pydantic de entrada/salida
├── services/       # Lógica de negocio
├── templates/      # Plantillas web
└── static/         # Recursos estáticos

docs/               # Documentación extendida del proyecto
tests/              # Tests automatizados
scripts/            # Scripts de arranque e inicialización
```

## Arranque rápido

1. Clona el repositorio.

```bash
git clone <URL_DEL_REPOSITORIO>
cd llm-governance-api-proxy
```

2. Copia el archivo de entorno:

```bash
cp .env.example .env
```

3. Genera una `SECRET_KEY`:

```bash
openssl rand -hex 32
```

4. Edita `.env` y configura como mínimo:
```env
SECRET_KEY=valor-generado-con-openssl
BOOTSTRAP_ADMIN_PASSWORD=AdminDemo123!
LLM_API_KEY=api-key-de-tu-proveedor-llm
LLM_BASE_URL=url-base-de-tu-proveedor-llm
LLM_MODEL=modelo-llm-que-quieres-usar
```

Credenciales iniciales solo para demo local:

- Usuario: `admin`
- Contraseña: `AdminDemo123!`

> Cambia la contraseña `BOOTSTRAP_ADMIN_PASSWORD` antes de usar el proyecto en un entorno real.

- `LLM_BASE_URL` es la URL base compatible con chat completions que te da tu proveedor LLM.
- `LLM_MODEL` es el modelo que quieres usar y queda registrado en los audit logs.


5. Levanta la app completa con Docker Compose:

```bash
docker compose up --build
```

En segundo plano:

```bash
docker compose up --build -d
```

6. Accede a la aplicación:

| Recurso | URL |
|---------|-----|
| UI web | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/v1/health |

7. Para parar los contenedores:

```bash
docker compose down
```
8. Para resetear también la base de datos:

```bash
docker compose down -v
```
> `docker compose down -v` borra el volumen de PostgreSQL: usuarios, admin bootstrap y audit logs.

### Desarrollo local (opcional)

Si quieres ejecutar el backend directamente en tu máquina, levanta solo PostgreSQL y arranca Uvicorn:

```bash
docker compose up -d db
python -m uvicorn app.main:app --reload
```

## Stack
| Categoría | Tecnología |
|-----------|-----------|
| Backend | Python 3.12+ / FastAPI |
| API documentation | OpenAPI / Swagger UI |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 |
| Authentication | JWT access + refresh tokens |
| Security | Argon2id password hashing  |
| Containers | Docker / Docker Compose |
| Testing | pytest |
