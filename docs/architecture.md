



## Decisiones de arquitectura
### Frontend: vanilla JS sin build step
- **Decisión:** HTML/CSS/JS vanilla servido aparte del backend, sin framework.
- **Por qué:** El MVP tiene 3 pantallas. Un framework JS añade complejidad innecesaria (npm, build, node_modules). Vanilla JS enseña los fundamentos y es trivial de migrar a React/Vue después.
- **Comunicación:** fetch() con URLs relativas (`/api/v1/...`). En MVP local se usa CORS en FastAPI. En producción se añade Nginx como proxy inverso sin tocar el frontend.

### Base de datos
- **PostgreSQL** como motor de base de datos para almacenar usuarios y registros de auditoría, garantizando integridad referencial y consistencia de los datos.
### Mapeo normativo orientativo
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

 **Aviso:** El cumplimiento normativo requiere revisión por un especialista legal según el contexto específico de cada empresa.
