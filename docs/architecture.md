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
| **Detector** | Service | Pipeline de 3 capas: regex endurecido → validación algorítmica (checksum) → exclusión por contexto negativo. Devuelve posiciones exactas de cada coincidencia para el enmascarado. Ver ADR-14. |
| **Policy** | Service | Decide acción (allow/mask/block) según categorías y prioridad |
| **Provider** | Service | Reenvía el array `messages` saneado (con marcadores si hubo mask + system de privacidad) al LLM externo y devuelve la respuesta del assistant |
| **Chat** | Service + Router | Orquestador para `/api/v1/chat`: recibe array `messages` → detector (re-detecta y sanea todo el array, no solo el último user) → policy → provider → logger → respuesta. Ver ADR-15. |
| **Logger** | Service + Repository | Guarda metadatos en audit_logs, consulta con filtros |
| **Scheduler** | Core | APScheduler: ejecuta limpieza de retención cada 24h |

## Flujo de una solicitud
```
Cliente (navegador, Gradio, OpenWebUI...)
  │  POST /api/v1/chat { messages: [{role, content}, ...] }
  │  (array completo, no solo el último turno)
  ▼
┌─────────────────────────────────┐
│ Middleware                       │
│  Auth:   valida JWT → user, rol │
│  Rate:   verifica IP no baneada │
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│ Chat Service                     │
│  Extrae array `messages`         │
│  (validación: ≥1 mensaje user)   │
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│ Detector                         │
│  Re-detecta y sanea TODOS los    │
│  mensajes con rol `user` del     │
│  array (no solo el último).      │
│  → ["contacto"]                  │
│  Ver ADR-15.                     │
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│ Policy                           │
│  contacto → mask                 │
│  (block > mask > allow)          │
│  Si mask: inyecta/actualiza      │
│  system con instrucción de       │
│  marcadores                      │
└───┬──────────┬──────────┬───────┘
    ▼          ▼          ▼
  ALLOW      MASK       BLOCK
    │          │          │
    │     ┌────▼────┐     │
    │     │Array    │     │
    │     │saneado: │     │
    │     │[EMAIL]  │     │
    │     │+ system │     │
    │     │ marker  │     │
    │     └────┬────┘     │
    ▼          ▼          │
┌─────────────────┐       │
│ Provider         │       │
│ POST → LLM API   │       │
│ messages array   │       │
│ (saneado, sin    │       │
│  persistir nada) │       │
│ ← respuesta      │       │
└────────┬─────────┘       │
         ▼                 ▼
┌─────────────────────────────────┐
│ Logger                           │
│  INSERT audit_logs               │
│  (request_id, user, action,     │
│   detected_categories, ...)      │
│  SIN prompt ni respuesta         │
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│ Respuesta JSON                   │
│  { request_id, action,          │
│    message, ... }                │
│  UI guarda turno en localStorage│
│  si allow/mask; no guarda       │
│  si block.                       │
└─────────────────────────────────┘
```

## Diagrama de despliegue
### Desarrollo local

```
┌──────────────────────────────────────────────┐
│  Desarrollo local                            │
│                                              │
│  ┌──────────────────┐  ┌──────────────────┐ │
│  │ uvicorn local    │  │ postgres:16      │ │
│  │ app.main:app     │──│ docker compose   │ │
│  │ puerto 8000      │  │ puerto 5432      │ │
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
│  │ Navegador        │  ↔ :8000              │
│  │                  │                        │
│  │ /          → redir│ (login/chat)          │
│  │ /login     → login│ (Jinja2 + HTMX)       │
│  │ /chat      → chat │ (Gradio demo)         │
│  │ /api/v1/*  → REST │ (fetch/JSON)          │
│  └──────────────────┘                        │
└──────────────────────────────────────────────┘
```


---

## ADRs
### ADR-1: UI server-rendered ligera + chat demo temporal

**Qué:** Pantallas internas simples servidas por FastAPI con Jinja2 + HTMX (p.ej. raíz `/` como redirección y login web en `/login`). El chat de usuario se ofrece como demo temporal con Gradio montado en `/chat`. La API REST sigue siendo el núcleo del producto bajo `/api/v1/*`.

**Por qué:** Para el MVP, Jinja2 + HTMX evita un build frontend separado y mantiene toda la lógica de sesión en el servidor (cookies HttpOnly). Gradio ofrece un chat funcional con ~10 líneas de integración, suficiente como demo mientras se evalúa OpenWebUI u otra UI definitiva. La API REST es independiente de la UI: cualquier cliente (Gradio, OpenWebUI, frontend estático futuro) se comunica por `/api/v1/*`.

**Decisiones tomadas:**
- Login único en `/login`. Redirección automática por rol: `user` → `/chat`, `admin` → `/dashboard`. La seguridad reside en los roles y el middleware `require_admin`, no en duplicar pantallas de login. Ver RF-18.
- Dashboard admin como puerta de entrada a herramientas administrativas (gestión de usuarios, audit logs). Implementación prevista con Jinja2 + HTMX.

**Trade-off:** Gradio no implementa auto-refresh del access token — si el token expira durante una sesión de chat, el usuario debe reautenticarse manualmente (ver TD-003). Gradio es pesado (~150 MB en disco) para una demo temporal; aceptable porque se prevé reemplazarlo en Beta. Jinja2 + HTMX escala mal si el número de pantallas crece mucho, pero para login + admin básico es suficiente.

---

### ADR-2: CORS local, Nginx solo en producción

**Qué:** En local, CORS en FastAPI. Nginx no se toca. En producción, Nginx como proxy inverso y CORS fuera.

**Por qué:** En local hay dos orígenes (puertos distintos) → CORS obligatorio. Nginx en local es un contenedor extra sin valor para el MVP.

**Trade-off:** Al desplegar en producción hay que añadir Nginx (~20 líneas de config) y quitar CORS. El frontend no cambia porque usa URLs relativas.

---

### ADR-3: Política de detección en código

**Qué:** Categorías, patrones regex y acciones (mask/block) definidas en un módulo Python. No en BD ni YAML.

**Por qué:** 3 categorías fijas para el MVP. Un archivo externo o tabla en BD añade parsing, validación y tooling innecesario. Cambiar una categoría ya implica escribir un regex nuevo: tocar código es inevitable.

**Trade-off:** Añadir categorías requiere redesplegar. Aceptable para un catálogo cerrado por diseño.

---

### ADR-4: Logs técnicos y de auditoría separados

**Qué:** Técnicos → stdout. Auditoría → tabla en PostgreSQL. Canales independientes.

**Por qué:** Los leen personas distintas (desarrollador vs admin). Mezclarlos expone metadatos al dev y obliga al admin a filtrar ruido.

**Trade-off:** Dos sistemas de logging. Coste mínimo: Python logger + inserción en BD.

---

### ADR-5: JWT access token (1h) + refresh token en BD

**Qué:** Access token JWT en cookie HttpOnly (1 hora, claims: `user_id`, `role`). Refresh token en BD para renovar sin pedir credenciales.

**Por qué:** 1 hora limita la ventana de riesgo si un admin desactiva un usuario. Tras caducar, el refresh token invalidado en BD impide renovar. Sin consulta a BD por petición (solo firma JWT).

**Trade-off:** Hasta 1 hora de ventana con token válido tras desactivación. Para un MVP con pocos usuarios, aceptable.

---

### ADR-6: Argon2id para hashing de credenciales

**Qué:** Argon2id para hashear contraseñas de admin y PINs de usuarios.

**Por qué:** Memory-hard: resiste ataques con GPU/ASIC. Recomendado por OWASP como estándar actual. Ya usado en proyecto anterior del desarrollador.

**Trade-off:** Verificación más lenta que bcrypt (~ms extra). Imperceptible para un login interactivo.

---

### ADR-7: Proveedor LLM único

**Qué:** Un solo proveedor LLM configurado por variables de entorno (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`). El cliente no elige proveedor en la petición.

**Por qué:** MVP simple. Multi-proveedor añade routing, failover y mapeo de esquemas de respuesta distintos sin valor para demostrar el concepto. El endpoint recibe `prompt` y lo demás lo resuelve el proxy.

**Trade-off:** Si el proveedor cae, el proxy no funciona. Para MVP es aceptable — cambiar de proveedor es cambiar variables de entorno y reiniciar.

---

### ADR-8: Detección por regex en MVP, migrable a NLP en futuro

**Qué:** Detección de datos sensibles con regex puro (módulo `re` de Python). Patrones definidos en un módulo intercambiable (`detector.py`). Sin dependencias externas.

**Por qué:** Los 3 tipos de datos del MVP (DNI, email, IBAN) tienen formato fijo y predecible. Regex es instantáneo (<1ms), sin descargas de modelos ni dependencias. Cada patrón es explícito y depurable: si hay un falso positivo, se ajusta la expresión. La interfaz del detector se diseña como módulo intercambiable para migrar a Presidio si el catálogo crece a datos sin formato fijo (nombres, direcciones).

**Trade-off:** Solo detecta formato, no contexto semántico (NLP). Los falsos positivos se mitigan con validación algorítmica (checksum) y exclusión posicional por contexto negativo — ver ADR-14 para el detalle por categoría. Si el catálogo se amplía a datos no estructurados, migrar a Presidio — el resto del sistema no cambia porque el detector es un módulo con interfaz fija.

---

### ADR-9: Limpieza de retención con APScheduler

**Qué:** APScheduler dentro del proceso FastAPI. Una tarea cada 24h ejecuta `DELETE FROM audit_logs WHERE timestamp < now() - interval '90 days'`. Al terminar, registra en logs técnicos: fecha, registros eliminados y rango cubierto.

**Por qué:** Automático sin configuración extra. Vive dentro del contenedor. Si el proceso está caído en el momento programado, los logs pendientes se borran en la siguiente ejecución — el peor caso son 24h extra de retención. El registro de cada ejecución demuestra que la política se cumple (accountability).

**Trade-off:** Si el contenedor está caído semanas, los logs se acumulan. Para MVP local con uso intermitente, aceptable. En producción se puede reforzar con `pg_cron` como respaldo.

---

---

### ADR-11: SlowAPI para rate limiting general

**Qué:** SlowAPI con backend `memory://` como rate limiter general en los endpoints del proxy. Se aplican decoradores `@limiter.limit` en endpoints sensibles (login, change_password). No se implementa throttling por fallos consecutivos en el MVP.

**Por qué:** Rate limiting clásico (límite de requests por ventana de tiempo) es un problema resuelto. SlowAPI lo cubre con decoradores y sin código manual. El throttling por fallos consecutivos (5 fallos → bloqueo 15 min, reset en acierto) es complejo, requiere estado persistente, y no aporta valor diferenciador al core del proxy.

**Trade-off:** SlowAPI en memoria no comparte estado entre workers, aceptable en MVP single-worker. Si se escala o Redis entra al stack, se cambia `memory://` por `redis://` sin tocar los decoradores.

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

### ADR-14: Pipeline de detección con validación algorítmica y exclusión contextual

**Qué:** El detector añade 2 capas sobre el regex base: validación algorítmica (checksum Luhn para tarjetas, MOD 97 para IBAN) y exclusión por contexto negativo (el match se descarta si está precedido por palabras como "pedido" o "factura").
Dirección postal queda excluida del MVP — requiere NLP, no regex.
| Patrón | Regex | Validación | Exclusión contextual | Justificación |
|--------|-------|-----------|---------------------|---------------|
| DNI | `(?<!\d)\d{8}[A-HJ-NP-TV-Z](?!\d)` | Módulo 23 (pospuesto a Fase 2) | — | El regex ya acota a 20 letras válidas. Solo ~4% de coincidencias aleatorias pasan. Si QA muestra ruido, se añade checksum. |
| NIF | `(?<!\d)[XYZ]\d{7}[A-HJ-NP-TV-Z](?!\d)` | Módulo 23 (pospuesto a Fase 2) | — | Ídem DNI. |
| CIF | `\b[A-HJ-NP-SUVW]\d{7}[A-Z0-9]\b` | Algoritmo CIF (pospuesto a Fase 2) | — | La letra inicial válida + dígito de control ya filtran ~70%. |
| Email | `\b[\w\.-]+@[\w\.-]+\.\w{2,}\b` | — | — | El formato de email es suficientemente restrictivo por sí solo. |
| Teléfono | `(?<!\d)[6-9]\d{8}(?!\d)` | — | `pedido`, `factura`, `ref`, `albarán`, `id`, `nº`, `expediente`, `caso`, `incidencia`, `ticket` | Números de 9 dígitos aparecen en contextos operativos (nº pedido, nº factura, nº expediente). La exclusión evita enmascarar referencias internas. |
| CP | `\b(?:CP\|código\s+postal\|cód\.\s*postal)\s*[:#.-]?\s*(\d{5})\b` | — | — | Solo detecta si está explícitamente etiquetado. Cero FP en importes, facturas o referencias. Sacrifica recall: no detecta "28001 Madrid" sin etiqueta. |
| IBAN | `\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b` | MOD 97 | — | El checksum IBAN es determinista y liviano (~15 líneas). Descarta ~99% de coincidencias aleatorias. |
| Tarjeta | `\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b` | Luhn (MOD 10) |  | |

**Por qué:** El regex puro produce falsos positivos que degradan la confianza (cualquier número de 5 dígitos como CP, cualquier secuencia de 16 dígitos como tarjeta). Microsoft Presidio valida este mismo pipeline de 3 capas con precisión > 95% en IBAN y tarjeta.
Los checksums son Python puro, sin dependencias externas — compatibles con ADR-8.

**Trade-off:** Checksums añaden < 0.1ms por validación. La exclusión contextual es frágil (depende de idioma y redacción): puede producir falsos negativos si el usuario escribe "mi pedido fue la tarjeta 4111...". Se acepta falso negativo > falso positivo
para experiencia de usuario. CP solo con prefijo explícito sacrifica recall pero garantiza cero falsos positivos en importes y referencias. Dirección postal se pospone a Beta con NLP (ADR-8).

---

### ADR-15: Chat multi-turn con re-detección completa del array en cada request

**Qué:** La UI envía el array completo `messages` en cada request al endpoint `/api/v1/chat`. El backend re-detecta y re-enmascara TODOS los mensajes con rol `user` del array, no solo el último turno. La UI es agnóstica a la detección.

**Por qué:** Privacidad (GDPR Art. 25, 32) no se delega al cliente. El navegador no es perímetro de confianza: `localStorage` es editable con DevTools, y un cliente modificado podría reenviar mensajes originales sin enmascarar en turnos posteriores. Re-detección por regex es <1ms por mensaje, despreciable. Single source of truth en backend: la lógica de privacidad vive en el proxy, no en el frontend.

**Trade-off:** CPU extra por request (~20ms para conversaciones de 20 mensajes). La detección NO se aplica a mensajes con rol `assistant` o `system`, solo a `user` — esto evita falsos positivos en respuestas generadas por el LLM. El historial de conversación lo mantiene el cliente en `localStorage` (no se persiste en backend), respetando RNF-3. Si la acción es `mask`, el backend inyecta/actualiza un mensaje `system` con la instrucción de privacidad sobre los marcadores `[EMAIL]`, `[DNI]`, `[TELEFONO]`, etc.

---


## Mapeo normativo
| Requisito del sistema | Regulación | Artículo | Cómo se cumple |
|---|---|---|---|
| RF-2, RF-3 — Detección + enmascarado | GDPR | Art. 25 — Protección de datos desde el diseño | Los datos personales se detectan y enmascaran antes de salir al proveedor |
| RF-5, RAL-3 — Trazabilidad | AI Act | Art. 12 — Mantenimiento de registros | Cada solicitud genera un registro con trazabilidad completa |
| RAL-1 — Minimización de datos | GDPR | Art. 5(1)(c) — Minimización | Solo se almacenan metadatos operativos, nunca el contenido |
| RAL-2 — Retención limitada | GDPR | Art. 5(1)(e) — Limitación de plazo | Los registros se eliminan automáticamente a los 90 días |
| RNF-3 — No persistir prompts ni respuestas | GDPR | Art. 5(1)(f) — Integridad y confidencialidad | El contenido sensible nunca llega a disco |
| RF-6 — Consulta de logs | GDPR | Art. 5(2) — Responsabilidad proactiva | El administrador puede generar evidencia documental de cumplimiento mediante los logs filtrables. El informe agregado (RF-19) queda pospuesto a Beta. |
| RNF-9 — Secrets por variables de entorno | GDPR | Art. 32 — Seguridad del tratamiento | Las credenciales nunca están en código fuente |
| RAL-4 — Transparencia de bloqueos | AI Act | Art. 13 — Transparencia y comunicación | El usuario sabe cuándo y por qué se bloqueó su solicitud |

> **Aviso:** Este mapeo es orientativo. El cumplimiento normativo requiere revisión por un especialista legal según el contexto específico de cada empresa.
---
