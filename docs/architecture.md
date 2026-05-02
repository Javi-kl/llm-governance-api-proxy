## Componentes y patrón de capas
### Patrón: router → service → repository

Tres capas con responsabilidades estrictas:

| Capa | Rol | Regla |
|---|---|---|
| **Router** | Recibe HTTP, valida entrada con Pydantic, delega al servicio | Solo HTTP y schemas |
| **Service** | Lógica de negocio, orquestación del flujo | Nunca toca HTTP ni BD directamente |
| **Repository** | Acceso a datos, queries SQLAlchemy | Nunca contiene lógica de negocio |

### Capas transversales

| Capa | Rol |
|---|---|
| **Schemas** | Modelos Pydantic de entrada/salida. Contrato de la API |
| **Dependencies** | FastAPI `Depends()`. Inyectan usuario autenticado, sesión BD, permisos |
| **Core** | Config (.env), seguridad (Argon2id, JWT), excepciones HTTP, rate limit, scheduler |
| **DB** | Conexión, modelos SQLAlchemy, migraciones |

### Componentes del sistema

| Componente | Capa | Responsabilidad |
|---|---|---|
| **Auth** | Router + Service + Dependencies | Login con JWT, refresh, creación/desactivación de usuarios |
| **Detector** | Service | Escanea el prompt con regex, devuelve categorías detectadas |
| **Policy** | Service | Decide acción (allow/mask/block) según categorías y prioridad |
| **Provider** | Service | Reenvía el prompt (original o enmascarado) al LLM externo |
| **Chat** | Service + Router | Orquestador: recibe prompt → detector → policy → provider → logger → respuesta |
| **Logger** | Service + Repository | Guarda metadatos en audit_logs, consulta con filtros, genera informe (RF-19) |
| **Scheduler** | Core | APScheduler: ejecuta limpieza de retención cada 24h |

## Flujo de una solicitud
```
Cliente
  │  POST /api/v1/chat { prompt }
  ▼
┌─────────────────────────────────┐
│ Middleware                       │
│  Auth:   valida JWT → user, rol │
│  Rate:   verifica IP no baneada │
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│ Detector                         │
│  Regex scan del prompt           │
│  → ["contacto"]                  │
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│ Policy                           │
│  contacto → mask                 │
│  (block > mask > allow)          │
└───┬──────────┬──────────┬───────┘
    │          │          │
    ▼          ▼          ▼
  ALLOW      MASK       BLOCK
    │          │          │
    │     ┌────▼────┐     │
    │     │Enmascara│     │
    │     │[EMAIL]  │     │
    │     │+ system │     │
    │     │ prompt  │     │
    │     └────┬────┘     │
    │          │          │
    ▼          ▼          │
┌─────────────────┐       │
│ Provider         │       │
│ POST → LLM API   │       │
│ ← respuesta      │       │
└────────┬─────────┘       │
         │                 │
         ▼                 ▼
┌─────────────────────────────────┐
│ Logger                           │
│  INSERT audit_logs               │
│  (request_id, user, action, ...) │
│  SIN prompt ni respuesta         │
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│ Respuesta JSON                   │
│  { request_id, action, ... }    │
│  Frontend decide qué mostrar     │
└─────────────────────────────────┘
```

## Diagrama de despliegue
### Desarrollo local

```
┌──────────────────────────────────────────────┐
│  docker-compose.yml                          │
│                                              │
│  ┌──────────────────┐  ┌──────────────────┐ │
│  │ proxy (uvicorn)  │  │ postgres:16      │ │
│  │ puerto 8000      │──│ puerto 5432      │ │
│  │                  │  │                  │ │
│  │ FastAPI +        │  │ DB: proxy_db     │ │
│  │ APScheduler      │  │ Tablas: users,   │ │
│  │                  │  │  refresh_tokens, │ │
│  │ CORS habilitado  │  │  audit_logs      │ │
│  └──────────────────┘  └────────┬─────────┘ │
│                                 │            │
│                          ┌──────▼─────────┐ │
│                          │ volumen: pgdata │ │
│                          │  /var/lib/...   │ │
│                          └────────────────┘ │
│                                              │
│  ┌──────────────────┐                        │
│  │ frontend/        │  ↔ fetch() a :8000   │
│  │ HTML/CSS/JS      │    con CORS          │
│  │ (Live Server)    │                        │
│  └──────────────────┘                        │
└──────────────────────────────────────────────┘
```

### Producción (futuro)

```
┌──────────────────────────────────────────────┐
│  VPS / servidor                              │
│                                              │
│  Internet                                    │
│     │                                        │
│     ▼                                        │
│  ┌──────────────────┐                        │
│  │ nginx            │ ← TLS, proxy inverso  │
│  │ puerto 443       │                        │
│  └───┬──────────┬───┘                        │
│      │          │                             │
│      ▼          ▼                             │
│  ┌────────┐ ┌──────────┐ ┌──────────────┐   │
│  │ /api/* │ │ /*       │ │ postgres:16   │   │
│  │ proxy  │ │ frontend │ │               │   │
│  │ :8000  │ │ estático │ └───────────────┘   │
│  └────────┘ └──────────┘                     │
└──────────────────────────────────────────────┘
```

---

## ADRs
### ADR-1: Frontend vanilla JS

**Qué:** HTML, CSS y JS sin framework. Sin npm, sin build. Archivos estáticos servidos aparte del backend.

**Por qué:** MVP pequeño (3 pantallas). `fetch()` a la API REST cubre toda la comunicación. Un framework añade complejidad que hoy no se necesita.

**Trade-off:** Sin componentes ni router. Si el proyecto crece a +10 pantallas, migrar a Vue/Svelte.

### ADR-2: CORS local, Nginx solo en producción

**Qué:** En local, CORS en FastAPI. Nginx no se toca. En producción, Nginx como proxy inverso y CORS fuera.

**Por qué:** En local hay dos orígenes (puertos distintos) → CORS obligatorio. Nginx en local es un contenedor extra sin valor para el MVP.

**Trade-off:** Al desplegar en producción hay que añadir Nginx (~20 líneas de config) y quitar CORS. El frontend no cambia porque usa URLs relativas.

### ADR-3: Política de detección en código

**Qué:** Categorías, patrones regex y acciones (mask/block) definidas en un módulo Python. No en BD ni YAML.

**Por qué:** 3 categorías fijas para el MVP. Un archivo externo o tabla en BD añade parsing, validación y tooling innecesario. Cambiar una categoría ya implica escribir un regex nuevo: tocar código es inevitable.

**Trade-off:** Añadir categorías requiere redesplegar. Aceptable para un catálogo cerrado por diseño.

### ADR-4: Logs técnicos y de auditoría separados

**Qué:** Técnicos → stdout. Auditoría → tabla en PostgreSQL. Canales independientes.

**Por qué:** Los leen personas distintas (desarrollador vs admin). Mezclarlos expone metadatos al dev y obliga al admin a filtrar ruido.

**Trade-off:** Dos sistemas de logging. Coste mínimo: Python logger + inserción en BD.

### ADR-5: JWT access token (1h) + refresh token en BD

**Qué:** Access token JWT en cookie HttpOnly (1 hora, claims: `user_id`, `role`). Refresh token en BD para renovar sin pedir credenciales.

**Por qué:** 1 hora limita la ventana de riesgo si un admin desactiva un usuario. Tras caducar, el refresh token invalidado en BD impide renovar. Sin consulta a BD por petición (solo firma JWT).

**Trade-off:** Hasta 1 hora de ventana con token válido tras desactivación. Para un MVP con pocos usuarios, aceptable.

### ADR-6: Argon2id para hashing de credenciales

**Qué:** Argon2id para hashear contraseñas de admin y PINs de usuarios.

**Por qué:** Memory-hard: resiste ataques con GPU/ASIC. Recomendado por OWASP como estándar actual. Ya usado en proyecto anterior del desarrollador.

**Trade-off:** Verificación más lenta que bcrypt (~ms extra). Imperceptible para un login interactivo.

### ADR-7: Proveedor LLM único

**Qué:** Un solo proveedor LLM configurado por variables de entorno (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`). El cliente no elige proveedor en la petición.

**Por qué:** MVP simple. Multi-proveedor añade routing, failover y mapeo de esquemas de respuesta distintos sin valor para demostrar el concepto. El endpoint recibe `prompt` y lo demás lo resuelve el proxy.

**Trade-off:** Si el proveedor cae, el proxy no funciona. Para MVP es aceptable — cambiar de proveedor es cambiar variables de entorno y reiniciar.

### ADR-8: Detección por regex en MVP, migrable a NLP en futuro

**Qué:** Detección de datos sensibles con regex puro (módulo `re` de Python). Patrones definidos en un módulo intercambiable (`detector.py`). Sin dependencias externas.

**Por qué:** Los 3 tipos de datos del MVP (DNI, email, IBAN) tienen formato fijo y predecible. Regex es instantáneo (<1ms), sin descargas de modelos ni dependencias. Cada patrón es explícito y depurable: si hay un falso positivo, se ajusta la expresión. La interfaz del detector se diseña como módulo intercambiable para migrar a Presidio si el catálogo crece a datos sin formato fijo (nombres, direcciones).

**Trade-off:** Solo detecta formato, no contexto. Posibles falsos positivos en teléfono (números sueltos). Si el catálogo se amplía a datos no estructurados, migrar a Presidio — el resto del sistema no cambia porque el detector es un módulo con interfaz fija.

### ADR-9: Limpieza de retención con APScheduler

**Qué:** APScheduler dentro del proceso FastAPI. Una tarea cada 24h ejecuta `DELETE FROM audit_logs WHERE timestamp < now() - interval '90 days'`. Al terminar, registra en logs técnicos: fecha, registros eliminados y rango cubierto.

**Por qué:** Automático sin configuración extra. Vive dentro del contenedor. Si el proceso está caído en el momento programado, los logs pendientes se borran en la siguiente ejecución — el peor caso son 24h extra de retención. El registro de cada ejecución demuestra que la política se cumple (accountability).

**Trade-off:** Si el contenedor está caído semanas, los logs se acumulan. Para MVP local con uso intermitente, aceptable. En producción se puede reforzar con `pg_cron` como respaldo.


---

## Mapeo normativo
| Requisito del sistema | Regulación | Artículo | Cómo se cumple |
|---|---|---|---|
| RF-2, RF-3 — Detección + enmascarado | GDPR | Art. 25 — Protección de datos desde el diseño | Los datos personales se detectan y enmascaran antes de salir al proveedor |
| RF-5, RAL-3 — Trazabilidad | AI Act | Art. 12 — Mantenimiento de registros | Cada solicitud genera un registro con trazabilidad completa |
| RAL-1 — Minimización de datos | GDPR | Art. 5(1)(c) — Minimización | Solo se almacenan metadatos operativos, nunca el contenido |
| RAL-2 — Retención limitada | GDPR | Art. 5(1)(e) — Limitación de plazo | Los registros se eliminan automáticamente a los 90 días |
| RNF-3 — No persistir prompts ni respuestas | GDPR | Art. 5(1)(f) — Integridad y confidencialidad | El contenido sensible nunca llega a disco |
| RF-6, RF-19 — Consulta de logs + informe | GDPR | Art. 5(2) — Responsabilidad proactiva | El administrador puede generar evidencia documental de cumplimiento |
| RNF-9 — Secrets por variables de entorno | GDPR | Art. 32 — Seguridad del tratamiento | Las credenciales nunca están en código fuente |
| RAL-4 — Transparencia de bloqueos | AI Act | Art. 13 — Transparencia y comunicación | El usuario sabe cuándo y por qué se bloqueó su solicitud |

> **Aviso:** Este mapeo es orientativo. El cumplimiento normativo requiere revisión por un especialista legal según el contexto específico de cada empresa.

---
