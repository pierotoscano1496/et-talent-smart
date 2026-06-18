# Checklist de Implementacion vs Spec

Fecha de auditoria: 2026-06-17

Este documento cruza el estado real del codigo actual con:

- `requirements.md`
- `design.md`
- `tasks.md`

Convenciones:

- `IMPLEMENTADO`: existe codigo funcional alineado con el spec.
- `PARCIAL`: existe estructura o parte de la logica, pero no cubre el requirement completo.
- `PENDIENTE`: no existe implementacion funcional todavia.
- `RIESGO`: hay diferencias entre lo especificado y lo codificado que pueden bloquear despliegue o pruebas.

## Resumen ejecutivo

| Requirement | Estado | Observacion corta |
|---|---|---|
| R1 Estudiantes y RFID | IMPLEMENTADO | Endpoints CRUD base, asociacion RFID y pruebas unitarias base ya existen |
| R2 Ambientes y nodos | IMPLEMENTADO | Gestion de ambientes, nodos, tokens y pruebas unitarias base ya existe; falta validacion runtime |
| R3 Control de acceso fisico | PARCIAL | Backend de eventos, heartbeat, listados y SSE HTTP existen; faltan firmware y cobertura mas profunda |
| R4 Autenticacion/autorizacion web | PARCIAL | `login`, `logout`, `change-password`, callbacks JWT y pruebas base ya existen; falta validacion runtime |
| R5 Monitoreo en tiempo real | PARCIAL | Ya existe endpoint SSE y eventos `node_status`; falta frontend |
| R6 Reportes | PARCIAL | `GET /reports/events`, `attendance-summary` y pruebas base existen; falta CSV/frontend |
| R7 Usuarios y roles web | PARCIAL | Gestion de usuarios web y pruebas unitarias base ya existen; faltan frontend y validacion runtime |
| R8 Comunicacion segura nodo-backend | PARCIAL | Token de nodo ya se valida contra su `node_id`; faltan TLS y firmware |
| R9 Despliegue y disponibilidad | PARCIAL | Hay Docker, migraciones, health y validacion unitaria por servicio, pero no esta listo end-to-end |

## Hallazgos transversales

- `docker-compose.yml` declara `frontend` y `nginx`, pero `frontend/`, `nginx/` y `firmware/` siguen vacios.
- Aun no existe carpeta raiz `tests/`, pero ya hay suites locales de `unittest` en `services/auth/tests/`, `services/access/tests/`, `services/management/tests/` y `services/reports/tests/`.
- `services/auth` ya acepta `DATABASE_URL` y mantiene fallback a `DATABASE_URI`.
- `docker-compose.yml` ya monta `db/init.sql` en `/docker-entrypoint-initdb.d/00-init.sql`.
- Los imports y entrypoints del backend fueron normalizados para ejecutarse dentro del contexto propio de cada microservicio.
- `docker compose config` valida sintaxis del archivo.
- Los cuatro microservicios backend ya pasaron al menos una validacion automatica local en Docker con `unittest` o `compileall`.
- El backend `postgres + auth + access + management + reports` ya fue levantado en conjunto y validado con smoke tests autenticados.
- La validacion del token de nodo ya cruza el token activo con el `node_id` reportado en el body.
- El stack completo con `frontend` y `nginx` sigue pendiente porque ambos directorios estan vacios.

## Checklist por requirement

### R1. Registro de Estudiantes y Llaves RFID

Estado: `IMPLEMENTADO`

Implementado:

- [x] Modelo `Estudiante` en `services/management/models/estudiante.py`
- [x] Modelo `TagRFID` en `services/management/models/tag_rfid.py`
- [x] Tablas `estudiante` y `tag_rfid` en `db/init.sql`
- [x] `POST /management/students`
- [x] `GET /management/students`
- [x] `PATCH /management/students/{id}`
- [x] `POST /management/students/{id}/rfid`
- [x] Validacion de duplicado `codigo-duplicado`
- [x] Validacion de tag en uso `tag-en-uso`
- [x] Desactivacion de estudiante
- [x] Preservacion de asociacion RFID en actualizacion parcial
- [x] JWT + rol `ADMINISTRADOR` en estos endpoints

Pendiente:

- [x] Pruebas unitarias base
- [ ] Property tests
- [ ] Verificacion runtime end-to-end con base de datos real

Evidencia:

- `services/management/routes/management.py` ya implementa estudiantes y asociacion RFID con paginacion y validaciones.
- `services/management/tests/test_management_routes.py` valida altas, conflictos, actualizacion parcial y asociacion RFID.

Relacion con tasks:

- `4.2` puede considerarse implementada a nivel de codigo.

### R2. Gestion de Ambientes y Nodos de Acceso

Estado: `IMPLEMENTADO`

Implementado:

- [x] Modelo `Ambiente`
- [x] Modelo `NodoAcceso`
- [x] Modelo `TokenNodo`
- [x] Tablas `ambiente`, `nodo_acceso` y `token_nodo`
- [x] `POST /management/environments`
- [x] `GET /management/environments`
- [x] `POST /management/nodes`
- [x] `PATCH /management/nodes/{id}/status`
- [x] `POST /management/nodes/{id}/token`
- [x] Validacion `nombre-ambiente-duplicado`
- [x] Validacion `identificador-nodo-duplicado`
- [x] Validacion `ambiente-no-encontrado`
- [x] Gestion del ciclo de vida del token del nodo
- [x] Denegacion por nodo inactivo en `POST /access/events`

Pendiente:

- [x] Pruebas automatizadas base
- [ ] Verificar runtime real de generacion, uso y revocacion de token entre `management` y `access`

Evidencia:

- `services/management/routes/management.py` ya implementa ambientes, nodos y operaciones de token.
- `services/management/tests/test_management_routes.py` valida ambientes, nodos y emision de token plano para el nodo.
- `services/access/routes/access.py` si persiste `denegado/nodo-inactivo` cuando el nodo esta inactivo.

Relacion con tasks:

- `4.3` y `4.4` pueden considerarse implementadas a nivel de codigo.
- `6.2` sigue parcial por lo demas.

### R3. Control de Acceso en el Nodo Fisico

Estado: `PARCIAL`

Implementado:

- [x] `POST /access/events`
- [x] Validacion basica de `tag_rfid`, `node_id` y `timestamp_utc`
- [x] Resolucion de nodo y tag RFID
- [x] Resultado `autorizado`
- [x] Resultado `denegado/tag-no-registrado`
- [x] Resultado `denegado/estudiante-inactivo`
- [x] Persistencia de `evento_acceso`
- [x] Publicacion al canal SSE interno en memoria
- [x] Heartbeat `POST /access/heartbeat`
- [x] Estado `sin-conexion` por ausencia de heartbeat
- [x] `GET /access/events`
- [x] `GET /access/nodes/status`
- [x] `GET /access/events/stream`
- [x] Pruebas automaticas base para `heartbeat`, listados y SSE

Pendiente:

- [ ] Cobertura automatizada completa del servicio
- [ ] Firmware ESP32 completo
- [ ] Timeout local de 2000 ms
- [ ] Apertura fisica por 3 segundos
- [ ] Registro local y politica de reintentos

Evidencia:

- Logica principal en `services/access/routes/access.py`.
- `services/access/heartbeat.py` monitorea heartbeats y marca nodos `sin-conexion`.
- `services/access/routes/access.py` ya implementa `events`, `nodes/status` y `events/stream`.
- `firmware/` esta vacio.

Relacion con tasks:

- `6.2` parcial.
- `6.3`, `6.4`, `6.5` pendientes.
- Bloque `11.x` pendiente.

### R4. Autenticacion y Autorizacion de Usuarios Web

Estado: `PARCIAL`

Implementado:

- [x] Factory Flask para auth
- [x] `GET /auth/health`
- [x] Dependencias JWT y bcrypt declaradas
- [x] Modelo `UsuarioWeb` local en `services/auth/models/usuario_web.py`
- [x] Modelo `TokenRevocado` local en `services/auth/models/token_revocado.py`
- [x] `POST /auth/login`
- [x] `POST /auth/logout`
- [x] `POST /auth/change-password`
- [x] Emision de JWT con claims adicionales `rol`, `nombre`, `primer_login`
- [x] Rechazo generico `credenciales-invalidas` en login
- [x] Hash y verificacion de password con bcrypt
- [x] Revocacion de tokens
- [x] Middleware y callbacks para token invalido, expirado y revocado
- [x] `roles_required(*roles)` aplicado en management, access y reports
- [x] Restricciones por rol en endpoints web protegidos
- [x] Pruebas automatizadas base

Pendiente:

- [ ] Verificacion runtime completa de autorizacion entre microservicios

Evidencia:

- `services/auth/routes/auth.py` ya implementa login, logout y change-password.
- `services/auth/app.py` ya registra callbacks de JWT revocado, expirado e invalido.
- `services/auth/tests/test_auth_routes.py` cubre login, logout, cambio de password y rechazo de JWT ausente o malformado.
- `services/management/authz.py`, `services/access/auth/web_roles.py` y `services/reports/authz.py` ya aplican revocacion JWT y `roles_required`.

Relacion con tasks:

- `2.3`, `2.4`, `2.5`, `10.1`, `10.2`, `10.3` y `10.4` ya estan implementadas en codigo.
- Queda pendiente su validacion runtime integrada.

### R5. Monitoreo en Tiempo Real del Ingreso

Estado: `PARCIAL`

Implementado:

- [x] Canal SSE interno `services/access/sse/events.py`
- [x] Endpoint SSE `GET /access/events/stream`
- [x] Emision real de eventos hacia cliente HTTP
- [x] Emision de cambios de conectividad de nodos

Pendiente:

- [ ] Frontend React/Vite
- [ ] Dashboard en tiempo real
- [ ] Filtros AND por ambiente, fecha y resultado
- [ ] Indicadores visuales `En linea` / `Sin conexion`

Evidencia:

- `services/access/routes/access.py` publica al canal interno y ya expone el stream SSE HTTP.
- `frontend/` esta vacio.

Relacion con tasks:

- `6.5`, `12.1`, `12.3`, `12.4` pendientes.

### R6. Generacion de Reportes de Asistencia

Estado: `PARCIAL`

Implementado:

- [x] `GET /reports/events`
- [x] Validacion de `fecha_inicio` y `fecha_fin`
- [x] Validacion de rango maximo de 90 dias
- [x] Validacion de limite maximo de 10 000 registros
- [x] Respuesta vacia con `total = 0`
- [x] Orden `timestamp_utc DESC`
- [x] Paginacion por `page` y `page_size`
- [x] `GET /reports/attendance-summary`
- [x] Pruebas automaticas base para `events` y `attendance-summary`

Pendiente:

- [ ] Exportacion CSV en frontend
- [ ] Garantia verificada de tiempo de respuesta <= 3000 ms
- [ ] Restricciones por rol verificadas con mayor cobertura

Evidencia:

- Implementacion en `services/reports/routes/reports.py`.
- `attendance-summary` ya agrega autorizados y denegados por ambiente.
- `frontend/` vacio, por lo que no existe exportacion CSV.

Relacion con tasks:

- `8.2` parcial.
- `8.3` pendiente.
- `12.6` pendiente.

### R7. Gestion de Roles y Usuarios del Sistema Web

Estado: `PARCIAL`

Implementado:

- [x] Modelo `UsuarioWeb` en `services/management/models/usuario_web.py`
- [x] Tabla `usuario_web` en `db/init.sql`
- [x] `POST /management/users`
- [x] `PATCH /management/users/{id}`
- [x] Duplicado `email-duplicado`
- [x] Cambio de rol
- [x] Desactivacion de usuario
- [x] Bloqueo de login para usuario inactivo
- [x] Pruebas automatizadas base

Pendiente:

- [ ] Flujo de primer login y cambio forzado de password en frontend
- [ ] Validacion runtime end-to-end

Evidencia:

- `services/management/routes/management.py` ya implementa alta y actualizacion de usuarios web.
- `services/auth/routes/auth.py` ya bloquea login de usuario inactivo y permite cambio de password.
- `services/management/tests/test_management_routes.py` cubre alta, duplicado de email y desactivacion de usuarios web.
- `frontend/` sigue vacio.

Relacion con tasks:

- `4.5`, `2.3` y `2.5` estan implementadas en codigo.
- `12.2` sigue pendiente.

### R8. Comunicacion Segura entre Nodos y Backend

Estado: `PARCIAL`

Implementado:

- [x] Decorador `node_token_required`
- [x] Rechazo con `401` ante token ausente, malformado o no activo
- [x] Registro en `bitacora_seguridad`
- [x] Flujo real validado: token de nodo generado en `management` y consumido por `access`

Pendiente:

- [ ] HTTPS/TLS real via Nginx
- [ ] Redireccion HTTP -> HTTPS
- [ ] Comportamiento del firmware ante `401`
- [ ] Politica de reintentos del firmware ante errores no `2xx`

Evidencia:

- Logica de validacion en `services/access/auth/node_token.py`.
- `services/access/routes/access.py` consume el nodo autenticado inyectado por el decorador.
- `services/management/routes/management.py` ya implementa `POST /management/nodes/{id}/token`.
- `nginx/` esta vacio.

Relacion con tasks:

- `6.1` parcial o implementada.
- `4.4`, `11.3`, `15.2` pendientes.

### R9. Despliegue y Disponibilidad del Sistema

Estado: `PARCIAL`

Implementado:

- [x] `docker-compose.yml`
- [x] Dockerfiles para microservicios Python
- [x] Health checks en auth, access, management y reports
- [x] Esquema SQL inicial y migracion Alembic
- [x] Volumen externo `postgres-data` declarado
- [x] Validacion automatica por servicio con Docker para backend
- [x] Arranque conjunto validado para `postgres`, `servicio-autenticacion`, `servicio-acceso`, `servicio-gestion` y `servicio-reportes`
- [x] Smoke test autenticado entre `auth`, `management`, `access` y `reports`

Pendiente:

- [ ] Frontend funcional dentro de Docker
- [ ] Nginx funcional dentro de Docker
- [x] Endpoint `/health` verificado en backend con compose levantado
- [ ] Respuesta `503` consistente cuando la BD no este disponible en todos los servicios y escenarios
- [ ] Manejo verificado de reinicio de contenedores
- [ ] Logica y pruebas de disponibilidad del 99%
- [ ] Smoke e integration tests completos del sistema

Riesgos:

- `frontend/` y `nginx/` estan vacios.
- Falta validar el stack completo expuesto por `nginx`, porque `frontend/` y `nginx/` aun no tienen implementacion funcional.

Relacion con tasks:

- `1.x` y `8.1` avanzadas.
- `13.x`, `15.x` y validacion real de despliegue pendientes.

## Prioridad recomendada de implementacion

### Bloque 1: Hacer operativo el backend base

- [x] Corregir bootstrap SQL inicial de PostgreSQL
- [x] Corregir variables de entorno de base de datos
- [x] Corregir imports y entrypoints de microservicios
- [x] Confirmar que `docker compose up` levanta auth, access, management y reports

### Bloque 2: Seguridad y auth web

- [x] Implementar `auth/login`
- [x] Implementar `auth/logout`
- [x] Implementar `auth/change-password`
- [x] Implementar revocacion JWT
- [x] Implementar `roles_required`
- [x] Agregar pruebas unitarias base de auth

### Bloque 3: Gestion administrativa

- [x] Estudiantes
- [x] RFID
- [x] Ambientes
- [x] Nodos
- [x] Usuarios web
- [x] Agregar pruebas unitarias base de management

### Bloque 4: Completar servicio de acceso

- [x] Heartbeat
- [x] Estado de conectividad
- [x] SSE HTTP real
- [x] Listados protegidos por JWT
- [x] Agregar pruebas unitarias base de access

### Bloque 5: Reportes y frontend

- [x] `attendance-summary`
- [x] Agregar pruebas unitarias base de reports
- [ ] Frontend de login
- [ ] Dashboard en tiempo real
- [ ] Reportes y CSV

### Bloque 6: Firmware, Nginx y pruebas

- [ ] Firmware ESP32
- [ ] Nginx/TLS
- [ ] Property-based tests
- [ ] Integracion y E2E

## Criterio practico para marcar un item como implementado

Antes de mover cualquier item de `PARCIAL` o `PENDIENTE` a `IMPLEMENTADO`, deberia cumplirse lo siguiente:

- existe endpoint o modulo funcional
- responde con el contrato esperado del spec
- persiste o consulta correctamente en base de datos cuando aplica
- esta protegido por auth o rol cuando aplica
- tiene al menos prueba unitaria o evidencia de verificacion local
