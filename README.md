[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136.1-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-AGPL%203.0-green.svg)](LICENSE)

> Proyecto para centralizar y controlar el uso de modelos LLM de terceros.
> Expone una API compatible con OpenAI. Inspecciona el historial de mensajes para detectar datos sensibles,
> aplica una política Block/Mask/Allow y genera trazabilidad de auditoría sin almacenar prompts ni respuestas.
> Incluye una UI web local, API documentada con Swagger y despliegue con Docker Compose.

> Documentación: [`architecture.md`](./docs/architecture.md) · [`overview.md`](./docs/overview.md) · [`requirements.md`](./docs/requirements.md)

> [Presentación](https://docs.google.com/presentation/d/1HGxZi3C1c7-zMwx_RuyBnGrLH2St4Rl2kG6m66cITv0/edit?usp=sharing)

> [Video](https://drive.google.com/file/d/1yx-5NoVuGaHAtT9YDc5FJv301_lRNaos/view?usp=sharing)
---

## Estructura del proyecto

Arquitectura por capas `Router → Service → Repository`.

```text
app/
├── core/           # Configuración, seguridad, excepciones, proveedor LLM y scheduler
├── db/             # Conexión a PostgreSQL y modelos SQLAlchemy
├── dependencies/   # Dependencias de FastAPI para auth y permisos
├── repositories/   # Acceso a datos
├── routers/        # Endpoints REST
├── schemas/        # Modelos Pydantic de entrada/salida
├── services/       # Lógica de negocio
└── ui/             # Chat Gradio, plantillas Jinja2 y estáticos

docs/               # Documentación extendida del proyecto
tests/              # Tests automatizados
scripts/            # Scripts de arranque e inicialización
```

## Arranque rápido

> El proyecto está pensado para infraestructura privada mediante Docker Compose; no incluye
despliegue público multiempresa.

1. Clona el repositorio.

```bash
git clone <URL_DEL_REPOSITORIO>
cd llm-governance-api-proxy
```

2. Copia el archivo de entorno:

```bash
cp .env.example .env
```

3. Edita `.env` y configura como mínimo:
```env
SECRET_KEY=valor-generado-con-openssl
BOOTSTRAP_ADMIN_PASSWORD=AdminDemo123!
LLM_API_KEY=api-key-de-tu-proveedor-llm
LLM_BASE_URL=url-base-de-tu-proveedor-llm
LLM_MODEL=modelo-llm-que-quieres-usar
```

- `SECRET_KEY` Genera una con: `openssl rand -hex 32`
- `LLM_BASE_URL` URL del proveedor compatible con la API de OpenAI.
- `LLM_MODEL` Modelo que quieres usar y queda registrado en los audit logs.


Credenciales iniciales solo para demo local:

- Usuario: `admin`
- Contraseña: `AdminDemo123!`

> Cambia la contraseña `BOOTSTRAP_ADMIN_PASSWORD` antes de usar el proyecto en un entorno real.

4. Levanta la app completa con Docker Compose:

```bash
docker compose up --build
```

En segundo plano:

```bash
docker compose up --build -d
```

5. Accede a la aplicación:

| Recurso | URL |
|---------|-----|
| UI web | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/v1/health |

6. Para parar los contenedores:

```bash
docker compose down
```
7. Para resetear también la base de datos:

```bash
docker compose down -v
```
> `docker compose down -v` borra el volumen de PostgreSQL: usuarios, admin bootstrap y audit logs.

## API compatible con OpenAI

El proxy expone una API compatible con el contrato de OpenAI en `/v1`
(chat completions + modelos): cualquier cliente de OpenAI funciona apuntando
la base URL a `http://localhost:8000/v1`.

1. Crea una API key (con la app levantada):

   ```bash
   docker compose exec -it app python -m scripts.create_api_key
   ```

   El script se ejecuta dentro del contenedor para usar las mismas
   dependencias y la misma BD que el proxy. La key solo se muestra una vez.

2. Configura tu cliente (UI de chat, librería, etc.) con:
   - Base URL: `http://localhost:8000/v1`
   - API key: la que imprime el script (`lgp_...`)

> ¿La UI corre en otra máquina que el proxy? Usa la dirección de red de esa máquina
> como base URL: `http://<hostname-del-proxy>:8000/v1`.

Para verificar la conexión sin una UI:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer lgp_..." \
  -H "Content-Type: application/json" \
  -d '{"model": "TU_MODELO", "messages": [{"role": "user", "content": "Hola"}]}'
```

Limitaciones del MVP: streaming debe configurarse en OFF en el cliente (no soportado);
los ajustes del cliente (p. ej. temperature) no se aplican;
el modelo debe ser el configurado (`LLM_MODEL`). 

## Stack
| Categoría | Tecnología |
|-----------|-----------|
| Backend | Python 3.12+ / FastAPI |
| API documentation | OpenAPI / Swagger UI |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 |
| Auth | JWT access + refresh tokens - API keys(clientes /v1) |
| Security | Argon2id password hashing  |
| Containers | Docker / Docker Compose |
| Testing | pytest |
