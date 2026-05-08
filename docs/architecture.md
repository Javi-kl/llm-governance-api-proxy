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
| **Chat** | Service + Router | Orquestador para ambos endpoints (`/api/v1/chat` y `/v1/chat/completions`): recibe prompt → detector → policy → provider → logger → respuesta |
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
    ▼          ▼          ▼
  ALLOW      MASK       BLOCK
    │          │          │
    │     ┌────▼────┐     │
    │     │Enmascara│     │
    │     │[EMAIL]  │     │
    │     │+ system │     │
    │     │ prompt  │     │
    │     └────┬────┘     │
    ▼          ▼          │
┌─────────────────┐       │
│ Provider         │       │
│ POST → LLM API   │       │
│ ← respuesta      │       │
└────────┬─────────┘       │
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

### ADR-10: Compatibilidad OpenAI API para Open WebUI

**Qué:** El proxy expone `POST /v1/chat/completions` con el mismo formato que la API de OpenAI. Open WebUI se conecta al proxy como si fuera el proveedor real. El proxy intercepta, escanea, aplica política y reenvía al proveedor configurado.

**Por qué:** Open WebUI es un frontend de chat profesional que las empresas ya usan. Implementar un chat desde cero (RF-10) cubre la demo mínima, pero conectar Open WebUI demuestra que el proxy funciona con herramientas reales sin fricción. El formato OpenAI es el estándar de facto — compatible también con AnythingLLM, LibreChat y otros clientes.

**Trade-off:** Dos endpoints de chat que mantener (`/api/v1/chat` propio + `/v1/chat/completions` compatible). La lógica del proxy (detector, policy, provider, logger) es compartida — solo cambia el adaptador de entrada/salida.

---

### ADR-11: SlowAPI para rate limiting general + lógica propia en login

**Qué:** SlowAPI con backend `memory://` como rate limiter general en los endpoints del proxy. El throttle de login (RF-16: 5 fallos → 15 min bloqueo, reset en acierto) se implementa con lógica propia sobre PostgreSQL porque ninguna librería genérica soporta el patrón "reset on success".

**Por qué:** Son dos problemas distintos. SlowAPI resuelve el rate limiting clásico con decoradores y sin código manual. El throttling de login necesita resetear el contador en acierto — eso solo lo da la lógica propia. Usar PostgreSQL evita añadir Redis solo para esto.

**Trade-off:** SlowAPI en memoria no comparte estado entre workers, aceptable en MVP single-worker. Si se escala o Redis entra al stack, se cambia `memory://` por `redis://` sin tocar los decoradores, y el throttle de login se migra a un Lua script atómico. La interfaz de `rate_limit.py` no cambia.

---

### ADR-12: Rollback genérico en get_db para MVP, acotado a futuro

**Qué:** `get_db` hace rollback con `except Exception`, no solo con `SQLAlchemyError`. Cualquier excepción no controlada que escape del servicio deshace la transacción entera.

**Por qué:** El commit es único y está al final de la petición. Si algo falla —sea de BD, de negocio o de red— el commit no se ejecuta, así que el rollback es inofensivo. Acotar a `SQLAlchemyError` exige que cada servicio maneje explícitamente todos sus errores de negocio, lo cual es más robusto pero añade fricción prematura en MVP.

**Trade-off:** Un servicio puede volverse vago con sus errores y delegar el rollback en `database.py` sin pensarlo. En Beta, cuando los servicios maduren y tengan manejo explícito por tipo de error, se acota a `SQLAlchemyError`.

---

### ADR-13: Un único administrador, sin creación de admins desde panel

**Qué:** El sistema soporta exactamente una cuenta de administrador. No existe endpoint, panel ni mecanismo para crear administradores adicionales en runtime. El único admin se crea vía bootstrap (RF-13).

**Por qué:** El MVP está dirigido a pymes y autónomos donde un único responsable técnico gestiona el acceso. Añadir multi-admin introduce complejidad de trazabilidad, escalada de privilegios y lógica de autorización que el producto no necesita en esta etapa. Varias personas pueden compartir la cuenta de admin si el contexto operativo lo requiere.

**Trade-off:** Si el admin olvida sus credenciales o deja la empresa, requiere intervención manual (BD directa o nuevo despliegue con bootstrap). Aceptable para MVP. En fase Beta, si el producto escala a equipos con necesidad de separación de responsabilidades, se evaluará añadir multi-admin con trazabilidad completa.

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