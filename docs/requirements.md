
## RFs

**RF-1. Proxy API — Endpoint principal**
- Historia: Como aplicación cliente, quiero enviar todas las solicitudes LLM a través del proxy para centralizar el control de uso en un único punto.
Criterios de aceptación:
- DADO QUE envío una solicitud autenticada con el array `messages` relleno (al menos un mensaje con rol `user`), CUANDO el proxy la recibe, ENTONCES re-detecta el array completo, sanea los mensajes user que lo requieran, y reenvía al proveedor el array saneado devolviendo la respuesta generada.
- DADO QUE el cuerpo de la solicitud está vacío o falta el campo `messages` o el array está vacío, CUANDO el proxy la recibe, ENTONCES devuelve error 422 con detalle del campo faltante.
- DADO QUE el array `messages` no contiene ningún mensaje con rol `user`, CUANDO el proxy la recibe, ENTONCES devuelve error 422 indicando que se requiere al menos un mensaje de usuario.
- DADO QUE la solicitud no incluye credenciales de autenticación, CUANDO el proxy la recibe, ENTONCES devuelve error 401.
- DADO QUE el proveedor externo no responde en el tiempo límite configurado, CUANDO el proxy reenvía la solicitud, ENTONCES devuelve error 504 con un mensaje controlado, sin exponer detalles del proveedor.
- DADO QUE la respuesta del proxy es `allow` o `mask`, CUANDO llega al cliente, ENTONCES la UI muestra la respuesta del LLM y guarda el turno (user + assistant) en `localStorage` para mantener historial entre requests.
- DADO QUE la respuesta del proxy es `block`, CUANDO llega al cliente, ENTONCES la UI muestra un mensaje amigable y NO guarda el turno bloqueado en el historial.
---
**RF-2. Detección de contenido sensible**
- Historia: Como sistema, quiero inspeccionar el contenido textual de cada solicitud antes de enviarla al proveedor para detectar categorías sensibles definidas en el MVP.

Categorías del MVP:
|Categoría	|Ejemplos de patrones detectables|
| --- | ---|
|identificacion|	DNI, NIF, CIF|
|contacto	|Email, teléfono, código postal|
|financiero	|IBAN, número de tarjeta de crédito|

Criterios de aceptación:
- DADO QUE el prompt contiene un DNI con formato válido, CUANDO el sistema lo inspecciona, ENTONCES detecta la categoría identificacion.
- DADO QUE el prompt contiene un email y un número de teléfono, CUANDO el sistema lo inspecciona, ENTONCES detecta la categoría contacto.
- DADO QUE el prompt contiene un IBAN válido, CUANDO el sistema lo inspecciona, ENTONCES detecta la categoría financiero.
- DADO QUE el prompt está vacío o solo contiene espacios, CUANDO el sistema lo inspecciona, ENTONCES no detecta ninguna categoría.
- DADO QUE el prompt contiene un dato que coincide parcialmente con un patrón (ej: DNI con una letra equivocada), CUANDO el sistema lo inspecciona, ENTONCES no lo detecta — solo los patrones completos activan la categoría.
---
**RF-3. Política de acción por categoría**
- Historia: Como responsable técnico, quiero que cada categoría sensible tenga una acción predefinida —permitir, enmascarar o bloquear— para que el sistema decida automáticamente cómo tratar cada solicitud según lo que contenga.
> La política está definida en código/configuración por el desarrollador. No es modificable por usuarios ni administradores desde la interfaz.

Mapeo para el MVP:
|Categoría | Acción |
| ---- | ---- |
|identificacion |	mask |
|contacto |	mask |
|financiero | block |

Categoría	| Marcador en el prompt
 --- | --
identificacion	|[DNI/NIF]
contacto	|[EMAIL] o [TELEFONO]

Regla de prioridad: si un prompt dispara varias categorías, gana la acción más restrictiva: block > mask > allow.
Criterios de aceptación:
- DADO QUE el array `messages` contiene un email en un mensaje user y la política para contacto es mask, CUANDO el sistema evalúa, ENTONCES sustituye el email por [EMAIL] en el mensaje donde aparece, inyecta la instrucción de privacidad en el system prompt solo si hay detección, y re-envía el array completo saneado al proveedor.
- DADO QUE el array `messages` contiene un dato sensible en un mensaje user NO terminal (turno anterior), CUANDO el sistema evalúa, ENTONCES lo enmascara también — la privacidad se aplica a todo el historial, no solo al último turno. Ver ADR-15.
- DADO QUE el array `messages` contiene dato sensible solo en mensajes con rol `assistant` o `system`, CUANDO el sistema evalúa, ENTONCES no se enmascaran — la detección aplica únicamente a mensajes con rol `user`.
- DADO QUE el array `messages` contiene un IBAN en un mensaje user y la política para financiero es block, CUANDO el sistema evalúa, ENTONCES bloquea la solicitud sin enviarla al proveedor.
- DADO QUE el array contiene un DNI (categoría mask) y un IBAN (categoría block) en mensajes user, CUANDO el sistema evalúa, ENTONCES se aplica block por ser la acción más restrictiva.
- DADO QUE el array no contiene ningún dato sensible en ningún mensaje user, CUANDO el sistema evalúa, ENTONCES la acción resultante es allow — no se modifica ni bloquea nada.
- DADO QUE no hay ninguna categoría definida en la configuración, CUANDO el sistema arranca, ENTONCES falla con un error de configuración explícito.
---
**RF-4. Respuesta estructurada del proxy**
- Historia: Como aplicación cliente, quiero recibir una respuesta JSON estructurada con el resultado del procesamiento para poder reaccionar de forma programática. El frontend decide qué información muestra al usuario final.
Criterios de aceptación:
- DADO QUE la solicitud fue allow, CUANDO el proxy responde, ENTONCES el JSON incluye: request_id, action: "allow", provider_response con el texto generado.
- DADO QUE la solicitud fue mask, CUANDO el proxy responde, ENTONCES el JSON incluye: request_id, action: "mask", provider_response con la respuesta del LLM.
- DADO QUE la solicitud fue block, CUANDO el proxy responde, ENTONCES el JSON incluye: request_id, action: "block", reason con las categorías que causaron el bloqueo. No incluye provider_response.
- DADO QUE el proveedor externo falla, CUANDO el proxy responde, ENTONCES el JSON incluye: request_id, action: "error", reason con un mensaje genérico. No expone detalles del proveedor ni stacks.
- DADO QUE varias categorías fueron detectadas, CUANDO el proxy responde para acciones mask o block, ENTONCES el campo detected_categories lista todas las categorías encontradas.
---
**RF-5. Trazabilidad mínima (registro de auditoría)**
- Historia: Como sistema, quiero registrar por cada solicitud un conjunto mínimo de metadatos —request_id, timestamp, usuario, proveedor, modelo, acción aplicada, categorías detectadas, latencia y estado— para disponer de trazabilidad sin guardar prompt ni respuesta completos.
> Se registran todas las solicitudes. El panel admin permite filtrar por action para distinguir incidencias de uso normal.
Criterios de aceptación:
- DADO QUE se procesa una solicitud con cualquier acción (allow, mask, block, error), CUANDO finaliza, ENTONCES se guarda en base de datos un registro con: request_id, timestamp, user_id, provider, model, action, detected_categories, latency_ms y status.
- DADO QUE el campo prompt o provider_response existe en el flujo interno, CUANDO se guarda el registro, ENTONCES dichos campos no se persisten.
- DADO QUE el proveedor falla, CUANDO se registra, ENTONCES status es "provider_error" y los metadatos disponibles hasta el fallo quedan registrados.
- DADO QUE un admin consulta los logs, CUANDO filtra por action=block, ENTONCES solo ve las solicitudes bloqueadas, ocultando las allow y mask.
---
**RF-7. Autenticación obligatoria en todas las solicitudes**
- Historia: Como sistema, quiero exigir autenticación del origen de cada solicitud para asociar cada uso a un usuario, servicio o aplicación identificable.
> Todas las solicitudes al proxy requieren sesión activa, excepto el propio endpoint de login y el health check.
Criterios de aceptación:
- DADO QUE envío una solicitud a cualquier endpoint del proxy con una cookie de sesión válida, CUANDO el sistema la recibe, ENTONCES procesa la solicitud normalmente.
- DADO QUE envío una solicitud sin cookie de sesión, CUANDO el sistema la recibe, ENTONCES devuelve error 401.
- DADO QUE envío una solicitud con una cookie que corresponde a una sesión expirada, CUANDO el sistema la recibe, ENTONCES devuelve error 401 con mensaje "sesión expirada".
- DADO QUE la solicitud es al endpoint /api/v1/auth/login o /api/v1/health, CUANDO el sistema la recibe sin autenticación, ENTONCES la procesa sin exigir sesión.
---
**RF-9. Catálogo cerrado de categorías sensibles**
- Historia: Como responsable técnico, quiero definir un catálogo inicial y cerrado de categorías sensibles del MVP para delimitar qué detecta el sistema y qué queda fuera.
> El sistema solo detecta lo que está en el catálogo. No usa ML ni heurísticas abiertas. Añadir una categoría requiere modificar código/configuración.

Catálogo del MVP:
Categoría	|Patrones
----|----
identificacion|	DNI, NIF, CIF
contacto	|Email, teléfono, código postal
financiero	|IBAN, nº tarjeta de crédito

Criterios de aceptación:
- DADO QUE el prompt contiene un dato que coincide con un patrón del catálogo, CUANDO el sistema inspecciona, ENTONCES lo detecta con la categoría correspondiente.
- DADO QUE el prompt contiene datos potencialmente sensibles pero que no coinciden con ningún patrón del catálogo (ej: fecha de nacimiento), CUANDO el sistema inspecciona, ENTONCES no los detecta y la solicitud se trata como allow.
- DADO QUE se intenta añadir una categoría en caliente sin reiniciar el sistema, CUANDO se consulta el catálogo activo, ENTONCES solo devuelve las categorías definidas en el arranque.
- DADO QUE el archivo de configuración de categorías tiene un patrón con sintaxis inválida, CUANDO el sistema arranca, ENTONCES falla con un error de configuración explícito indicando qué categoría y qué patrón falló.
---
**RF-13. Bootstrap del primer administrador**
- Historia: Como sistema, quiero disponer de un mecanismo de bootstrap que cree el primer usuario administrador durante el despliegue inicial, sin exponer un endpoint de registro público de administradores.
> No existe POST /auth/register público para admin. El primer admin se crea desde variables de entorno en el primer arranque. No es posible crear admins adicionales desde el panel de administración (RF-17 gestiona únicamente usuarios con rol user).
Criterios de aceptación:
- DADO QUE el sistema arranca por primera vez con las variables de entorno BOOTSTRAP_ADMIN_PASSWORD definida y no existe ningún admin en base de datos, CUANDO el sistema inicia, ENTONCES crea automáticamente el usuario admin.
- DADO QUE el sistema arranca y ya existe al menos un admin en base de datos, CUANDO el sistema inicia, ENTONCES ignora las variables de bootstrap y no crea duplicados.
- DADO QUE el sistema arranca sin la variable BOOTSTRAP_ADMIN_PASSWORD y no existe ningún admin en base de datos, CUANDO el sistema inicia, ENTONCES falla con un mensaje claro: "No hay admin en BD y BOOTSTRAP_ADMIN_PASSWORD no está definida".
- DADO QUE la contraseña de bootstrap no cumple la política mínima de seguridad (longitud, complejidad), CUANDO el sistema inicia, ENTONCES falla indicando que la contraseña de bootstrap es demasiado débil.
---
**RF-14. Roles mínimos user y admin**
- Historia: Como sistema, quiero distinguir dos roles —user y admin— para separar el uso operativo del proxy de la administración del sistema.
> Cada cuenta tiene exactamente un rol. El rol se asigna al crear el usuario y no cambia en runtime (MVP).
Criterios de aceptación:
- DADO QUE un usuario con rol user autenticado intenta acceder a un endpoint del proxy (/api/v1/chat), CUANDO el sistema verifica permisos, ENTONCES permite el acceso.
- DADO QUE un usuario con rol user autenticado intenta acceder a un endpoint de administración (/api/v1/admin/*), CUANDO el sistema verifica permisos, ENTONCES devuelve error 403.
- DADO QUE un usuario con rol admin autenticado intenta acceder a un endpoint de administración, CUANDO el sistema verifica permisos, ENTONCES permite el acceso.
- DADO QUE un usuario con rol admin autenticado intenta usar el chat (/api/v1/chat), CUANDO el sistema verifica permisos, ENTONCES permite el acceso — el admin también puede usar el proxy.
- DADO QUE un usuario tiene un valor de rol no reconocido (ni user ni admin), CUANDO intenta acceder a cualquier endpoint, ENTONCES el sistema devuelve error 403 y registra la incidencia en logs técnicos.
---
**RF-15. Autenticación con PIN (user) y contraseña (admin)**
- Historia: Como sistema, quiero autenticar a los usuarios normales mediante PIN numérico y a los administradores mediante contraseña robusta, adaptando el mecanismo al perfil de riesgo de cada rol.
> Un único endpoint (POST /api/v1/auth/login) que recibe `username` + `credential`. El sistema **NO** pide el rol al cliente — el rol se determina por el usuario encontrado en la base de datos. Tanto users como admins comparten la misma tabla (`users`) diferenciados por el campo `role`. El frontend presenta un único formulario de login (ver RF-18) y el backend es agnóstico al origen del login.
Criterios de aceptación:
- DADO QUE envío `username` y `credential` correctos, CUANDO hago login, ENTONCES el sistema devuelve un JWT en cookie HttpOnly con el rol correspondiente al usuario encontrado.
- DADO QUE envío credenciales incorrectas, CUANDO hago login, ENTONCES el sistema devuelve 401 con mensaje genérico "credenciales inválidas" — sin revelar si el usuario existe.
- DADO QUE envío un `username` que no existe, CUANDO hago login, ENTONCES el sistema devuelve 401 con el mismo mensaje genérico.
- DADO QUE un usuario inactivo intenta hacer login, CUANDO el sistema verifica el estado, ENTONCES devuelve 401 con mensaje genérico.
- DADO QUE envío el body sin el campo `username`, CUANDO hago login, ENTONCES el sistema devuelve 422 indicando que username es obligatorio.
- DADO QUE envío el body sin el campo `credential`, CUANDO hago login, ENTONCES el sistema devuelve 422 indicando que credential es obligatorio.
- DADO QUE un usuario normal envía su username y PIN correcto (5-6 dígitos), CUANDO hace login, ENTONCES el sistema crea una sesión y devuelve cookie con rol user.
- DADO QUE un administrador envía su username y contraseña correcta, CUANDO hace login, ENTONCES el sistema crea una sesión y devuelve cookie con rol admin.
- DADO QUE un usuario envía un PIN incorrecto, CUANDO hace login, ENTONCES el sistema devuelve error 401 con mensaje genérico "credenciales inválidas" — sin revelar si el usuario existe o no.
- DADO QUE un administrador envía una contraseña incorrecta, CUANDO hace login, ENTONCES el sistema devuelve error 401 con el mismo mensaje genérico que para usuario.
- DADO QUE la contraseña tiene menos de la longitud mínima configurada, CUANDO se establece (creación o reseteo), ENTONCES el sistema rechaza con error de validación.
---
**RF-6. Consulta del historial de auditoría**
- Historia: Como usuario administrador, quiero consultar un historial de solicitudes con filtros básicos para revisar decisiones, incidencias y uso del sistema.
> Solo accesible por admin. Un user recibe 403. Los filtros son: action, user_id, desde/hasta (fechas), y paginación (page, page_size).
Criterios de aceptación:
- DADO QUE un admin consulta /api/v1/admin/logs sin filtros, CUANDO solicita la primera página, ENTONCES recibe una lista paginada con todas las solicitudes registradas, ordenadas por fecha descendente.
- DADO QUE un admin filtra por action=block, CUANDO consulta los logs, ENTONCES solo ve las solicitudes bloqueadas.
- DADO QUE un admin filtra por rango de fechas (desde y hasta), CUANDO consulta los logs, ENTONCES solo ve solicitudes dentro de ese rango.
- DADO QUE un admin filtra por user_id, CUANDO consulta los logs, ENTONCES solo ve solicitudes de ese usuario.
- DADO QUE los filtros no devuelven resultados, CUANDO el admin consulta, ENTONCES recibe una lista vacía con total: 0, sin error.
- DADO QUE un admin envía un valor de filtro inválido (ej: action=invalid), CUANDO consulta, ENTONCES recibe error 422 indicando qué filtro y qué valores son válidos.
- DADO QUE un usuario con rol user intenta acceder al endpoint de logs, CUANDO consulta, ENTONCES recibe error 403.
---
**RF-8. Formato de error controlado y consistente**
- Historia: Como sistema, quiero devolver errores en un formato JSON controlado y consistente cuando falle el proveedor externo o la validación interna, para no exponer detalles técnicos ni romper la integración.
> Todo error HTTP del sistema sigue el mismo sobre: { "error": { "code": "...", "message": "..." } }. El campo code es legible por máquina, message es legible por humano pero sin detalles internos.
Criterios de aceptación:
- DADO QUE ocurre un error de validación (422), CUANDO el sistema responde, ENTONCES el cuerpo incluye code: "VALIDATION_ERROR", message descriptivo y details con los campos fallidos.
- DADO QUE ocurre un error de autenticación (401), CUANDO el sistema responde, ENTONCES el cuerpo incluye code: "UNAUTHORIZED" y message sin revelar si el usuario existe.
- DADO QUE ocurre un error de permisos (403), CUANDO el sistema responde, ENTONCES el cuerpo incluye code: "FORBIDDEN" y message indicando que el rol no tiene acceso.
- DADO QUE ocurre un error inesperado del servidor (500), CUANDO el sistema responde, ENTONCES el cuerpo incluye code: "INTERNAL_ERROR" y un message genérico. No expone stack traces ni detalles de la excepción.
- DADO QUE el proveedor externo devuelve un error (4xx o 5xx), CUANDO el sistema responde al cliente, ENTONCES el código HTTP es 502 y el cuerpo incluye code: "UPSTREAM_ERROR" con message genérico, sin reenviar la respuesta original del proveedor.
- DADO QUE el proveedor no responde (timeout), CUANDO el sistema responde, ENTONCES el código HTTP es 504 y el cuerpo incluye code: "UPSTREAM_TIMEOUT" con message genérico.
---
**RF-10. Chat MVP para usuario normal**
- Historia: Como usuario normal, quiero una interfaz web sencilla para escribir un prompt, enviarlo al proxy, y ver la respuesta del LLM o un mensaje de bloqueo, para entender el funcionamiento del sistema.
> El usuario normal nunca ve términos técnicos (action, mask, detected_categories). Solo ve la respuesta del LLM o un mensaje amigable si fue bloqueado.
Criterios de aceptación:
- DADO QUE el usuario escribe un prompt sin datos sensibles y pulsa enviar, CUANDO el proxy responde, ENTONCES la interfaz muestra la respuesta del LLM formateada.
- DADO QUE el prompt es bloqueado por política, CUANDO el proxy responde, ENTONCES la interfaz muestra un mensaje amigable: "Tu mensaje contiene información que no podemos procesar. Por favor, reformúlalo sin incluir datos sensibles."
- DADO QUE el prompt fue enmascarado, CUANDO el proxy responde, ENTONCES la interfaz muestra la respuesta del LLM normalmente — el usuario no sabe que su prompt fue modificado.
- DADO QUE el usuario envía el formulario con el campo vacío, CUANDO hace clic en enviar, ENTONCES la interfaz muestra un error de validación antes de llamar al proxy.
- DADO QUE la llamada al proxy falla por error de red o timeout, CUANDO la interfaz recibe el error, ENTONCES muestra un mensaje: "El servicio no está disponible en este momento. Inténtalo de nuevo."
- DADO QUE el usuario no ha iniciado sesión, CUANDO intenta acceder a la página del chat, ENTONCES la interfaz redirige a la pantalla de login.
---
**RF-12. Health check**
- Historia: Como sistema, quiero un endpoint de health check para confirmar que el proxy y sus dependencias están operativos.
> Endpoint público — no requiere autenticación. Verifica conectividad con la base de datos.
Criterios de aceptación:
- DADO QUE el proxy y la base de datos están operativos, CUANDO se llama a GET /api/v1/health, ENTONCES devuelve 200 con { "status": "healthy", "database": "connected" }.
- DADO QUE la base de datos no responde, CUANDO se llama a GET /api/v1/health, ENTONCES devuelve 503 con { "status": "unhealthy", "database": "disconnected" }.
- DADO QUE el proxy está arrancando y la base de datos aún no está lista, CUANDO se llama a GET /api/v1/health, ENTONCES devuelve 503 indicando qué dependencia falla.
- DADO QUE se llama al health check sin credenciales, CUANDO el sistema recibe la petición, ENTONCES responde normalmente sin exigir autenticación.
---
**RF-16. Rate limiting básico**
- Historia: Como sistema, quiero limitar la tasa de peticiones por IP para evitar abuso y proteger los endpoints sensibles.
> Se implementa con SlowAPI. Límite global por defecto: 100 peticiones/minuto por IP.
> El endpoint de login tiene límite más restrictivo: 5 peticiones cada 5 minutos por IP.
> No se implementa throttling por fallos consecutivos ni bloqueo temporal en el MVP.
Criterios de aceptación:
- DADO QUE una IP hace más de 100 peticiones/minuto a cualquier endpoint, CUANDO supera el límite, ENTONCES el sistema devuelve 429.
- DADO QUE una IP hace más de 5 peticiones en 5 minutos al endpoint de login, CUANDO supera el límite, ENTONCES el sistema devuelve 429.
---
**RF-17. Gestión de usuarios desde panel admin**
- Historia: Como usuario administrador, quiero crear, desactivar y resetear el PIN de usuarios normales desde el panel de administración para gestionar el acceso sin intervención técnica.
> Solo accesible por admin. Las operaciones son exclusivamente sobre usuarios con rol user. No se puede crear, modificar ni eliminar admins desde este panel. El sistema opera con un único administrador.
Criterios de aceptación:
- DADO QUE un admin crea un usuario con un username y PIN válidos (5-6 dígitos), CUANDO envía el formulario, ENTONCES el usuario queda creado con rol user y estado activo.
- DADO QUE un admin desactiva un usuario existente, CUANDO confirma la acción, ENTONCES el usuario pasa a estado inactivo y sus sesiones activas se invalidan.
- DADO QUE un admin intenta desactivar un usuario ya inactivo, CUANDO envía la acción, ENTONCES el sistema devuelve error 422 indicando que el usuario ya está inactivo.
- DADO QUE un admin resetea el PIN de un usuario, CUANDO envía el nuevo PIN, ENTONCES el PIN del usuario se actualiza y sus sesiones activas se invalidan.
- DADO QUE un admin envía un PIN con formato inválido al crear o resetear, CUANDO el sistema valida, ENTONCES devuelve error 422 con el formato esperado.
- DADO QUE un admin intenta crear un usuario con un username que ya existe, CUANDO envía el formulario, ENTONCES el sistema devuelve error 409 indicando el conflicto.
- DADO QUE un admin intenta modificar o desactivar una cuenta con rol admin, CUANDO envía la acción, ENTONCES el sistema devuelve error 422 indicando que los admins no se gestionan desde este panel.
- DADO QUE un usuario con rol user intenta acceder al endpoint de gestión, CUANDO hace la petición, ENTONCES recibe error 403.
- DADO QUE no hay usuarios creados, CUANDO el admin consulta la lista, ENTONCES recibe una lista vacía con total: 0.
---
**RF-18. Login único con redirección por rol**
- Historia: Como sistema, quiero un único formulario de inicio de sesión que redirija automáticamente según el rol del usuario autenticado, para simplificar la experiencia sin duplicar pantallas.
> Un único endpoint visual en `/login`. El backend recibe `username` + `credential`, determina el rol por el usuario encontrado en base de datos, y redirige: `user` → `/chat`, `admin` → `/dashboard`. La seguridad real reside en los roles y en el middleware `require_admin`, no en tener pantallas separadas. El dashboard admin (`/dashboard`) es una página Jinja2 + HTMX que sirve como puerta de entrada a las herramientas administrativas (gestión de usuarios, audit logs, informe de cumplimiento). No está implementado aún.
Criterios de aceptación:
- DADO QUE un usuario con rol `user` inicia sesión con credenciales válidas, CUANDO el backend autentica, ENTONCES redirige a `/chat`.
- DADO QUE un usuario con rol `admin` inicia sesión con credenciales válidas, CUANDO el backend autentica, ENTONCES redirige a `/dashboard`.
- DADO QUE un usuario con sesión activa intenta acceder a `/login`, CUANDO la página carga, ENTONCES redirige automáticamente a su vista correspondiente (`/chat` o `/dashboard`) sin mostrar el formulario.
- DADO QUE un usuario con rol `user` intenta acceder directamente a `/dashboard`, CUANDO el sistema verifica permisos, ENTONCES recibe error 403.
- DADO QUE un usuario con rol `admin` intenta acceder a `/chat`, CUANDO el sistema verifica permisos, ENTONCES permite el acceso — el admin también puede usar el proxy.
- DADO QUE se envían credenciales inválidas desde `/login`, CUANDO el backend rechaza, ENTONCES se muestra un mensaje genérico sin revelar si el usuario existe ni cuál es su rol.
---
**RF-19. Informe de cumplimiento (Should)**
- Historia: Como responsable de cumplimiento, quiero generar un informe resumido por rango de fechas para disponer de evidencia estructurada ante auditorías internas o externas.
> Solo accesible por admin. No es un dashboard visual — es un endpoint que devuelve datos agregados en JSON. El frontend lo muestra como tabla descargable.
Criterios de aceptación:
- DADO QUE un admin solicita el informe sin fechas, CUANDO llama al endpoint, ENTONCES recibe los datos agregados del periodo completo (desde la primera solicitud registrada).
- DADO QUE un admin solicita el informe con desde y hasta, CUANDO llama al endpoint, ENTONCES recibe solo los datos de ese rango.
- DADO QUE hay solicitudes en el rango, CUANDO se genera el informe, ENTONCES incluye: total_solicitudes, desglose_por_accion (allow / mask / block / error), categorias_mas_detectadas (top 5) y ultima_limpieza_retencion (fecha y registros eliminados).
- DADO QUE no hay solicitudes en el rango, CUANDO se solicita el informe, ENTONCES devuelve todos los contadores a cero con total_solicitudes: 0, sin error.
- DADO QUE un usuario con rol user intenta acceder, CUANDO llama al endpoint, ENTONCES recibe error 403.
---
## RNFs
**RNF-1. Despliegue reproducible con Docker**
- Historia: Como responsable técnico, quiero desplegar el sistema mediante Docker y configuración reproducible para poder instalarlo, ejecutarlo y evaluarlo de forma consistente.
> Todo lo necesario para arrancar está en docker-compose.yml y .env.example. Sin pasos manuales, sin "en mi máquina funciona".
Criterios de aceptación:
- DADO QUE clono el repositorio y copio .env.example a .env, CUANDO ejecuto docker compose up, ENTONCES el proxy y PostgreSQL arrancan sin errores.
- DADO QUE el sistema arranca por primera vez, CUANDO la base de datos no tiene tablas, ENTONCES las migraciones se ejecutan automáticamente en el arranque.
- DADO QUE falta el archivo .env al arrancar, CUANDO ejecuto docker compose up, ENTONCES el sistema falla con un mensaje claro indicando las variables obligatorias.
- DADO QUE detengo los contenedores con docker compose down, CUANDO los vuelvo a levantar, ENTONCES los datos persistidos en el volumen de PostgreSQL se conservan.

---
**RNF-3. No almacenar prompts ni respuestas**
- Historia: Como responsable del sistema, quiero almacenar solo metadatos operativos y de auditoría, excluyendo por defecto el contenido completo de prompts y respuestas, para reducir riesgo y complejidad.
> Ni una línea de prompt ni de respuesta en base de datos. Si en el futuro se necesita, será una decisión explícita con su propio RF.
Criterios de aceptación:
- DADO QUE se procesa una solicitud, CUANDO se guarda el registro de auditoría, ENTONCES los campos prompt y provider_response no existen en la tabla de logs.
- DADO QUE un desarrollador inspecciona el modelo de datos de logs, CUANDO revisa las columnas, ENTONCES no encuentra ninguna columna que almacene texto de prompt o respuesta.
- DADO QUE se consultan los logs desde el panel admin, CUANDO se muestra un registro, ENTONCES no aparece el contenido del prompt ni de la respuesta en ningún campo.
- DADO QUE el sistema está en desarrollo y se usa un logger, CUANDO se registra información, ENTONCES los prompts y respuestas completos no aparecen en los logs de aplicación por defecto.
---
**RNF-6. Acceso restringido a logs de auditoría**
- Historia: Como responsable técnico, quiero restringir el acceso a los registros de auditoría a usuarios administradores para evitar exposición innecesaria de metadatos.
> Los metadatos de auditoría contienen user_id, action, detected_categories. Un user normal no debe ver solicitudes de otros usuarios ni estadísticas de uso.
Criterios de aceptación:
- DADO QUE un usuario con rol user intenta acceder a cualquier endpoint bajo /api/v1/admin/*, CUANDO hace la petición, ENTONCES recibe error 403.
- DADO QUE un usuario con rol admin accede a los endpoints de logs, CUANDO consulta, ENTONCES recibe los datos sin restricción.
- DADO QUE un usuario no autenticado intenta acceder a los logs, CUANDO hace la petición, ENTONCES recibe error 401.
- DADO QUE un admin consulta los logs, CUANDO ve los registros, ENTONCES los metadatos mostrados no incluyen información que permita reconstruir el contenido del prompt o la respuesta.
---
**RNF-9. Configuración crítica por variables de entorno**
- Historia: Como responsable técnico, quiero que la configuración crítica (API keys, secrets) se gestione exclusivamente por variables de entorno para separar configuración del código.
> Ningún secreto en el código fuente ni en archivos de configuración trackeados en git.
Criterios de aceptación:
- DADO QUE inspecciono el código fuente del proyecto, CUANDO busco valores de API keys o secrets, ENTONCES no encuentro ninguno hardcodeado — solo referencias a variables de entorno.
- DADO QUE la variable de entorno LLM_API_KEY no está definida, CUANDO el proxy intenta llamar al proveedor, ENTONCES falla con un error de configuración claro, sin revelar defaults ni rutas de archivo.
- DADO QUE la variable LLM_API_KEY está definida, CUANDO el proxy reenvía la solicitud al proveedor, ENTONCES incluye la key en la cabecera de autenticación correspondiente.
- DADO QUE se añade una variable de entorno nueva pero no está documentada en .env.example, CUANDO otro desarrollador clona el proyecto, ENTONCES el sistema falla con un mensaje que indica exactamente qué variable falta.
---
**RNF-2. Separación de logs técnicos y de auditoría**
- Historia: Como responsable técnico, quiero separar los logs técnicos de los registros de auditoría funcional para distinguir operación del sistema y trazabilidad de gobernanza.
> Logs técnicos = errores, warnings, arranque, conexiones (para el desarrollador). Logs de auditoría = registros de cada solicitud (para el admin, RF-5). Son canales distintos.
Criterios de aceptación:
- DADO QUE ocurre un error de conexión a PostgreSQL, CUANDO el sistema arranca, ENTONCES el error aparece en los logs técnicos (consola) pero no genera un registro de auditoría.
- DADO QUE se bloquea una solicitud por política, CUANDO se registra, ENTONCES aparece en los logs de auditoría (tabla en BD) pero no en los logs técnicos salvo nivel debug.
- DADO QUE un desarrollador revisa los logs técnicos, CUANDO busca una solicitud concreta, ENTONCES no encuentra metadatos de auditoría — esa información está en la base de datos, no en stdout.
- DADO QUE un admin consulta los logs de auditoría, CUANDO revisa un registro, ENTONCES no ve stack traces ni errores internos del sistema — eso va en logs técnicos.
---
**RNF-4. Latencia limitada y estable**
- Historia: Como usuario interno, quiero que el proxy añada una latencia limitada y estable sobre la llamada al proveedor para que el uso siga siendo válido en escenarios interactivos.
> El proxy no debe ralentizar la experiencia. La validación de datos sensibles debe ser imperceptible comparada con el tiempo de generación del LLM.
Criterios de aceptación:
- DADO QUE se procesa un prompt sin datos sensibles, CUANDO se mide el tiempo total de la solicitud, ENTONCES la inspección del proxy añade menos de 200ms sobre el tiempo de respuesta del proveedor.
- DADO QUE se procesa un prompt con múltiples datos sensibles de varias categorías, CUANDO se mide, ENTONCES la inspección completa (detección + enmascarado) añade menos de 500ms.
- DADO QUE el sistema está sometido a 10 solicitudes concurrentes, CUANDO se mide la latencia, ENTONCES el tiempo extra del proxy se mantiene dentro del límite sin degradación significativa.
---
**RNF-7. UI de demo separada del núcleo**
- Historia: Como responsable técnico, quiero mantener la UI de demo separada del núcleo del proxy para evitar acoplar la capa de demostración con la lógica principal del sistema.
> Frontend y backend son proyectos independientes. El proxy funciona sin el frontend. El frontend se comunica solo por API.
Criterios de aceptación:
- DADO QUE levanto solo el backend sin el frontend, CUANDO llamo a los endpoints desde cURL o Swagger, ENTONCES todas las funcionalidades del proxy operan normalmente.
- DADO QUE el frontend se cae o no se despliega, CUANDO otro sistema llama a la API del proxy, ENTONCES no hay impacto en su funcionamiento.
- DADO QUE reviso la estructura del proyecto, CUANDO miro las dependencias del backend, ENTONCES no encuentro librerías de plantillas HTML ni de servido de estáticos usadas para la UI de demo.
- DADO QUE el frontend necesita una nueva funcionalidad, CUANDO requiere un endpoint que no existe, ENTONCES se añade al backend como API y el frontend lo consume — sin lógica de presentación en el backend.

---
## RALs
**RAL-1. Minimización de datos**
- Historia: Como responsable del producto, quiero que el diseño del sistema aplique minimización de datos para tratar y almacenar solo la información necesaria para el control y la trazabilidad básica.
> Principio rector. Cada dato que se guarda debe tener una razón justificada. Lo confirman RF-5 y RNF-3.
Criterios de aceptación:
- DADO QUE se procesa una solicitud, CUANDO se almacena el registro de auditoría, ENTONCES cada campo guardado tiene un propósito concreto documentado (trazabilidad, control de costes, detección de incidencias).
- DADO QUE se propone añadir un campo nuevo al registro de auditoría, CUANDO se evalúa, ENTONCES debe estar justificado en un requisito funcional — no se añaden campos "por si acaso".
- DADO QUE el sistema recibe datos personales en un prompt, CUANDO los detecta, ENTONCES los enmascara o bloquea sin persistirlos nunca.
---
**RAL-2. Retención limitada de metadatos**
- Historia: Como responsable del producto, quiero definir una política de retención limitada para los metadatos almacenados para no conservar información más tiempo del necesario.
> MVP: 90 días fijos. Pasado ese plazo, los registros se eliminan automáticamente. No configurable por interfaz.
Criterios de aceptación:
- DADO QUE un registro de auditoría tiene más de 90 días, CUANDO se ejecuta la limpieza programada, ENTONCES el registro se elimina de la base de datos.
- DADO QUE un registro tiene 89 días o menos, CUANDO se ejecuta la limpieza, ENTONCES el registro se conserva intacto.
- DADO QUE la base de datos está vacía o no hay registros que limpiar, CUANDO se ejecuta la limpieza, ENTONCES la operación termina sin error.
- DADO QUE la limpieza falla por un error de base de datos, CUANDO ocurre, ENTONCES el error se registra en logs técnicos pero no interrumpe el funcionamiento del proxy.
- DADO QUE se ejecuta la limpieza programada, CUANDO finaliza, ENTONCES se registra en logs del sistema: fecha, número de registros eliminados y rango de fechas cubierto.
---
**RAL-3. Trazabilidad básica de decisiones**
- Historia: Como responsable del producto, quiero disponer de trazabilidad básica de las decisiones del sistema para poder reconstruir qué ocurrió en cada solicitud y aportar evidencia mínima de uso.
> Dado un request_id, puedo responder: quién, cuándo, qué proveedor, qué acción, qué categorías se detectaron y cuál fue el resultado.
Criterios de aceptación:
- DADO QUE recupero un registro de auditoría por request_id, CUANDO leo sus campos, ENTONCES puedo saber: qué usuario hizo la solicitud, cuándo, a qué proveedor, qué acción se aplicó, qué categorías se detectaron y si tuvo éxito o error.
- DADO QUE un usuario hace múltiples solicitudes, CUANDO filtro los logs por user_id, ENTONCES puedo reconstruir la secuencia temporal de sus solicitudes.
- DADO QUE se bloquea una solicitud, CUANDO consulto el registro, ENTONCES el campo detected_categories contiene las categorías exactas que causaron el bloqueo.
- DADO QUE el sistema no guarda el prompt ni la respuesta, CUANDO consulto un registro, ENTONCES no puedo ver el contenido original, pero sí sé qué decisión se tomó y por qué.
---
**RAL-4. Transparencia para el usuario sobre bloqueos (Should)**
- Historia: Como usuario interno, quiero saber cuándo una solicitud ha sido bloqueada por política para tener transparencia operativa sobre la actuación del sistema.
> Solo se informa del bloqueo. El enmascarado es transparente para el usuario (RF-10).
Criterios de aceptación:
- DADO QUE el proxy bloquea una solicitud, CUANDO la interfaz de chat muestra el resultado, ENTONCES el usuario ve un mensaje claro indicando que su mensaje no se envió por contener datos sensibles.
- DADO QUE el proxy enmascara una solicitud, CUANDO la interfaz muestra la respuesta del LLM, ENTONCES el usuario no recibe ninguna notificación de que su prompt fue modificado.
- DADO QUE un admin revisa el log de un bloqueo, CUANDO consulta el detalle, ENTONCES ve qué categorías se detectaron, pero sin ver el contenido del prompt.
