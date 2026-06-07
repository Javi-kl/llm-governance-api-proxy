# llm-governance-api-proxy
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-AGPL%203.0-green.svg)](LICENSE)

> Este proyecto implementa una API proxy para centralizar y controlar el uso de modelos LLM de terceros en pymes y autónomos. Antes de reenviar cada solicitud al proveedor externo, inspecciona el texto para detectar categorías sensibles, aplica una política simple de permitir, enmascarar o bloquear, y genera trazabilidad mínima útil para auditoría sin almacenar por defecto el contenido completo de prompts y respuestas. El MVP se acompaña de una UI web local sencilla y de una API documentada con Swagger para demostrar su funcionamiento e integración.

> Documentación: [`architecture.md`](./docs/architecture.md) · [`overview.md`](./docs/overview.md) · [`requirements.md`](./docs/requirements.md)

---
## Casos de uso en MVP
| Caso de uso | Valor | Riesgo a controlar |
| ---- | ---- | ---- |
| **Chatbot de atención al cliente** | *Reduce carga del equipo, evita envío accidental de datos sensibles y mantiene un servicio de atención más estable.* | *El cliente puede pegar datos personales, números de pedido o incidencias con información sensible.* |
| **Asistente interno para empleados** | *Ahorra tiempo al equipo y evita que se usen datos sensibles sin control.* | *Un empleado puede incluir datos de compañeros, clientes, nóminas o incidencias internas.* |
---
## Arranque rápido

1. Clona el repositorio
2. Copia `.env.example` a `.env` y configura `LLM_API_KEY`
3. Levanta PostgreSQL: `docker compose up -d db`
4. Arranca el backend: `python -m uvicorn app.main:app --reload`
5. UI web: http://localhost:8000
6. Swagger: http://localhost:8000/docs

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
