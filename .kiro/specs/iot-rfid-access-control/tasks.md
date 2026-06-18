# Implementation Plan: IoT RFID Access Control

## Overview

Plan de implementación incremental del sistema de control de acceso RFID IoT. El orden de construcción respeta las dependencias: infraestructura base → microservicios backend (autenticación → gestión → acceso → reportes) → firmware ESP32 → frontend React → integración y pruebas → configuración final Nginx/TLS.

Lenguajes y runtimes: Python 3.11 + Flask (backend), C/Arduino (firmware ESP32), TypeScript + React 18 (frontend).

---

## Tasks

- [x] 1. Infraestructura base: Docker Compose, PostgreSQL y migraciones
  - [x] 1.1 Crear estructura de directorios del repositorio
    - Crear carpetas: `services/auth`, `services/access`, `services/management`, `services/reports`, `firmware/`, `frontend/`, `nginx/`, `db/migrations/`
    - Crear `.gitignore` con entradas para Python, Node y artefactos de build
    - _Requirements: 9.1_

  - [x] 1.2 Definir `docker-compose.yml` con todos los servicios y red interna
    - Declarar servicios: `postgres`, `servicio-autenticacion`, `servicio-acceso`, `servicio-gestion`, `servicio-reportes`, `frontend`, `nginx`
    - Configurar red interna `acceso-net`; exponer solo el puerto 443 del Nginx hacia el host
    - Agregar volumen externo `postgres-data` montado en `/var/lib/postgresql/data`
    - Añadir `restart: on-failure:3` y `depends_on` con `condition: service_healthy` para cada microservicio
    - _Requirements: 9.1, 9.4, 9.6_

  - [x] 1.3 Crear esquema SQL inicial y script de migraciones con Alembic
    - Crear tablas: `usuario_web`, `token_revocado`, `estudiante`, `tag_rfid`, `ambiente`, `nodo_acceso`, `token_nodo`, `evento_acceso`, `bitacora_seguridad` según el modelo ER del diseño
    - Definir índices: `evento_acceso(timestamp_utc DESC)`, `evento_acceso(nodo_id, timestamp_utc DESC)`, `evento_acceso(estudiante_id, timestamp_utc DESC)`, `tag_rfid(uid_hex) WHERE activo = TRUE`
    - Crear script `db/init.sql` que ejecute la migración inicial al arrancar el contenedor de PostgreSQL
    - _Requirements: 3.8, 6.1, 9.4_

  - [x] 1.4 Crear `Dockerfile` base compartido para microservicios Python
    - Usar imagen `python:3.11-slim`; instalar dependencias desde `requirements.txt`; configurar `gunicorn` como entrypoint
    - Añadir health check: `HEALTHCHECK CMD curl -f http://localhost:${PORT}/health || exit 1`
    - _Requirements: 9.1, 9.3_

- [ ] 2. Servicio_Autenticacion (puerto 5001)
  - [x] 2.1 Crear estructura del proyecto Flask para Servicio_Autenticacion
    - Inicializar app Flask con factory pattern (`create_app`)
    - Configurar SQLAlchemy con `pool_pre_ping=True` y `SQLALCHEMY_DATABASE_URI` desde variable de entorno
    - Implementar middleware de health check en `GET /auth/health` que retorna `{"status": "ok"}` solo cuando PostgreSQL responde; retorna HTTP 503 con `{"error": "base-datos-no-disponible"}` en caso contrario
    - _Requirements: 9.3, 9.5_

  - [-] 2.2 Implementar almacenamiento de contraseñas con bcrypt y modelo `UsuarioWeb`
    - Crear modelo SQLAlchemy `UsuarioWeb` con campos: `id (UUID PK)`, `nombre_completo`, `email (UK)`, `password_hash`, `rol`, `estado`, `primer_login`, `created_at`, `updated_at`
    - Implementar `hash_password(plain: str) -> str` usando `bcrypt` con factor de coste 12
    - Implementar `verify_password(plain: str, hashed: str) -> bool`
    - Crear script de seed para insertar un administrador inicial con contraseña temporal
    - _Requirements: 4.3, 7.1_

  - [ ] 2.3 Implementar `POST /auth/login` con emisión de JWT
    - Validar credenciales contra `UsuarioWeb`; si el usuario tiene `estado = "inactivo"` retornar HTTP 401 con `{"error": "credenciales-invalidas"}`
    - Si las credenciales son correctas, emitir JWT HS256 con claims: `sub`, `rol`, `nombre`, `primer_login`, `iat`, `exp = iat + 8h`
    - Retornar HTTP 200 con `{"token", "rol", "nombre", "primer_login"}`; en cualquier fallo retornar HTTP 401 con `{"error": "credenciales-invalidas"}` sin revelar cuál campo falló
    - _Requirements: 4.1, 4.2, 7.4_

  - [ ] 2.4 Implementar `POST /auth/logout` y modelo `TokenRevocado`
    - Crear modelo `TokenRevocado` con campos: `id`, `jti (UK)`, `revocado_en`, `expira_en`, `usuario_id (FK)`
    - En `POST /auth/logout`: extraer el `jti` del JWT, insertar en `token_revocado`, retornar HTTP 200 con `{"mensaje": "sesion-cerrada"}`
    - Implementar decorador/middleware `jwt_required_with_revocation` que, además de validar firma y expiración, consulta `token_revocado`; retorna HTTP 401 si el `jti` está en la lista
    - _Requirements: 4.4, 4.9_

  - [ ] 2.5 Implementar `POST /auth/change-password`
    - Validar JWT activo; verificar contraseña actual; actualizar `password_hash` con bcrypt coste 12; actualizar `primer_login = False`
    - _Requirements: 7.5_

  - [ ]* 2.6 Escribir pruebas unitarias para Servicio_Autenticacion
    - Casos: login exitoso (ADMINISTRADOR, AUXILIAR_EDUCACION), credenciales incorrectas, usuario inactivo, logout invalida token, cambio de contraseña
    - _Requirements: 4.1, 4.2, 4.9, 7.4_

  - [ ]* 2.7 Escribir property test para Property 7: JWT válido contiene claims obligatorios y coherentes
    - **Property 7: JWT válido contiene claims obligatorios y coherentes**
    - **Validates: Requirements 4.1**

  - [ ]* 2.8 Escribir property test para Property 8: Credenciales incorrectas producen respuesta genérica
    - **Property 8: Credenciales incorrectas producen respuesta genérica**
    - **Validates: Requirements 4.2**

  - [ ]* 2.9 Escribir property test para Property 19: Desactivación de usuario web bloquea autenticación
    - **Property 19: Desactivación de usuario web bloquea autenticación**
    - **Validates: Requirements 7.4**

- [ ] 3. Checkpoint — Servicio_Autenticacion
  - Ejecutar `pytest tests/unit/test_servicio_autenticacion.py tests/properties/test_properties_autenticacion.py`; asegurar que todos los tests pasen antes de continuar. Consultar al usuario si surgen dudas.

- [ ] 4. Servicio_Gestion (puerto 5003)
  - [x] 4.1 Crear estructura Flask y modelos SQLAlchemy para Servicio_Gestion
    - Inicializar app Flask con factory pattern; reutilizar configuración SQLAlchemy del paso 2.1
    - Crear modelos: `Estudiante`, `TagRFID`, `Ambiente`, `NodoAcceso`, `TokenNodo`, `UsuarioWeb` (referencia, sin duplicar lógica)
    - Implementar `GET /management/health`
    - _Requirements: 1.1, 2.1, 7.1, 9.3, 9.5_

  - [-] 4.2 Implementar endpoints de gestión de Estudiantes
    - `POST /management/students`: validar campos (nombre ≤100, código alfanumérico ≤20, grado ≤20); insertar con `estado = "activo"`; retornar HTTP 409 `{"error": "codigo-duplicado"}` si código ya existe
    - `GET /management/students`: listar con paginación
    - `PATCH /management/students/{id}`: actualización parcial de `nombre_completo`, `grado_seccion`, `estado`; conservar `tag_rfid` asociado
    - `POST /management/students/{id}/rfid`: asociar `uid_hex` (hex 8 chars); retornar HTTP 409 `{"error": "tag-en-uso"}` si ya está asignado
    - Todos los endpoints requieren JWT con rol ADMINISTRADOR; retornar HTTP 403 si el rol es insuficiente
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 4.5, 4.6_

  - [ ] 4.3 Implementar endpoints de gestión de Ambientes
    - `POST /management/environments`: validar campos (nombre ≤80, descripción ≤255, ubicación ≤120, estado); retornar HTTP 409 `{"error": "nombre-ambiente-duplicado"}` si nombre ya existe
    - `GET /management/environments`: listar con paginación
    - _Requirements: 2.1, 2.2, 4.5_

  - [ ] 4.4 Implementar endpoints de gestión de Nodos de Acceso
    - `POST /management/nodes`: validar `identificador` (alfanumérico ≤40), `id_ambiente` existente; retornar HTTP 409 `{"error": "identificador-nodo-duplicado"}` o HTTP 422 `{"error": "ambiente-no-encontrado"}`
    - `PATCH /management/nodes/{id}/status`: habilitar/deshabilitar nodo sin eliminar eventos previos
    - `POST /management/nodes/{id}/token`: generar, revocar o regenerar token de nodo; almacenar hash del token en `token_nodo`; retornar HTTP 200 con estado actualizado
    - _Requirements: 2.3, 2.4, 2.5, 2.6, 8.3_

  - [ ] 4.5 Implementar endpoints de gestión de Usuarios Web
    - `POST /management/users`: crear usuario con `nombre_completo`, `email`, contraseña temporal (hasheada con bcrypt coste 12), `rol`; retornar HTTP 409 `{"error": "email-duplicado"}` si email ya existe
    - `PATCH /management/users/{id}`: actualizar `rol` o `estado`; conservar historial de actividad
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 4.6 Escribir pruebas unitarias para Servicio_Gestion
    - Casos: creación exitosa de estudiante/ambiente/nodo/usuario, duplicados, actualización parcial, desactivación
    - _Requirements: 1.1–1.7, 2.1–2.6, 7.1–7.4_

  - [ ]* 4.7 Escribir property test para Property 3: Unicidad de identificadores clave
    - **Property 3: Unicidad de identificadores clave**
    - **Validates: Requirements 1.3, 2.2, 7.2**

  - [ ]* 4.8 Escribir property test para Property 4: Unicidad y exclusividad del tag RFID
    - **Property 4: Unicidad y exclusividad del tag RFID**
    - **Validates: Requirements 1.4**

  - [ ]* 4.9 Escribir property test para Property 5: Actualización parcial preserva asociaciones
    - **Property 5: Actualización parcial preserva asociaciones**
    - **Validates: Requirements 1.7**

  - [ ]* 4.10 Escribir property test para Property 6: Desactivación preserva integridad histórica
    - **Property 6: Desactivación preserva integridad histórica**
    - **Validates: Requirements 1.6, 2.6**

- [ ] 5. Checkpoint — Servicio_Gestion
  - Ejecutar `pytest tests/unit/test_servicio_gestion.py tests/properties/test_properties_gestion.py`; asegurar que todos los tests pasen antes de continuar. Consultar al usuario si surgen dudas.

- [ ] 6. Servicio_Acceso (puerto 5002)
  - [x] 6.1 Crear estructura Flask y lógica de verificación de token de nodo
    - Inicializar app Flask con factory pattern
    - Implementar decorador `node_token_required`: extrae `Authorization: Bearer <token>`, computa hash, busca en `token_nodo` con `estado = "activo"`; si ausente/malformado/revocado → retornar HTTP 401 `{"error": "token-nodo-invalido"}` e insertar registro en `bitacora_seguridad` (timestamp, node_identifier, motivo, ip_origen)
    - Implementar `GET /access/health`
    - _Requirements: 8.1, 8.2, 9.3, 9.5_

  - [-] 6.2 Implementar `POST /access/events` — procesamiento de evento RFID
    - Validar body: `tag_rfid` (hex 8 chars), `node_id` (string), `timestamp_utc` (ISO 8601)
    - Verificar que el nodo existe y tiene `estado = "activo"`; si nodo inactivo → persistir evento con `resultado = "denegado"`, `codigo_resultado = "nodo-inactivo"` → retornar HTTP 200
    - Buscar `tag_rfid` en `tag_rfid` WHERE `activo = TRUE`; según estado del estudiante determinar resultado: "autorizado", "denegado/estudiante-inactivo" o "denegado/tag-no-registrado"
    - Insertar `evento_acceso` con todos los campos requeridos: `id, tag_rfid, nodo_id, ambiente_id, estudiante_id (nullable), timestamp_utc, resultado, codigo_resultado`
    - Publicar evento al canal SSE interno
    - Retornar HTTP 200 con `{"resultado", "codigo_resultado", "evento_id"}` dentro de 1000 ms
    - _Requirements: 2.7, 3.2, 3.4, 3.5, 3.6, 3.8_

  - [ ] 6.3 Implementar `POST /access/heartbeat` y lógica de estado de conectividad
    - Validar token de nodo; actualizar `nodo_acceso.ultimo_heartbeat = NOW()` y `estado_conectividad = "en-linea"`
    - Crear tarea background (APScheduler o thread daemon) que cada 30 s consulte nodos cuyo `ultimo_heartbeat < NOW() - 120s` y actualice `estado_conectividad = "sin-conexion"`
    - Publicar evento SSE de tipo `node_status` cuando cambie el estado de conectividad
    - _Requirements: 3.9, 5.4, 5.5_

  - [ ] 6.4 Implementar `GET /access/events` (listado paginado) y `GET /access/nodes/status`
    - `GET /access/events`: requiere JWT; retornar eventos paginados (100 por página máx) ordenados `timestamp_utc DESC`
    - `GET /access/nodes/status`: requiere JWT; retornar lista de nodos con `estado_conectividad` actual
    - _Requirements: 3.8, 5.4, 5.5_

  - [ ] 6.5 Implementar `GET /access/events/stream` — Server-Sent Events
    - Endpoint SSE que emite `Content-Type: text/event-stream`; requiere JWT en header `Authorization`
    - Mantener cola de eventos por conexión; emitir eventos de acceso y de estado de nodo
    - Formato de cada mensaje SSE según diseño: `data: {evento_id, estudiante, ambiente, timestamp, resultado}` y `data: {tipo: "node_status", node_id, estado}`
    - _Requirements: 5.1, 5.2, 5.4, 5.5_

  - [ ]* 6.6 Escribir pruebas unitarias para Servicio_Acceso
    - Casos: evento con tag autorizado, tag no registrado, estudiante inactivo, nodo inactivo, token de nodo inválido, heartbeat actualiza estado
    - _Requirements: 2.7, 3.4–3.9, 8.1, 8.2_

  - [ ]* 6.7 Escribir property test para Property 1: Resultado de acceso determinado por estado del estudiante
    - **Property 1: Resultado de acceso determinado por estado del estudiante**
    - **Validates: Requirements 3.4, 3.5, 3.6**

  - [ ]* 6.8 Escribir property test para Property 2: Nodo inactivo deniega todos los accesos
    - **Property 2: Nodo inactivo deniega todos los accesos**
    - **Validates: Requirements 2.7**

  - [ ]* 6.9 Escribir property test para Property 12: Token de nodo revocado es rechazado y auditado sin persistir evento
    - **Property 12: Token de nodo revocado es rechazado y auditado sin persistir evento**
    - **Validates: Requirements 8.1, 8.2**

  - [ ]* 6.10 Escribir property test para Property 13: Persistencia completa de cada evento de acceso
    - **Property 13: Persistencia completa de cada evento de acceso**
    - **Validates: Requirements 3.8**

- [ ] 7. Checkpoint — Servicio_Acceso
  - Ejecutar `pytest tests/unit/test_servicio_acceso.py tests/properties/test_properties_acceso.py`; asegurar que todos los tests pasen. Consultar al usuario si surgen dudas.

- [ ] 8. Servicio_Reportes (puerto 5004)
  - [x] 8.1 Crear estructura Flask de solo lectura para Servicio_Reportes
    - Inicializar app Flask; configurar SQLAlchemy en modo solo lectura (mismo `DATABASE_URI`)
    - Implementar `GET /reports/health`
    - _Requirements: 9.3, 9.5_

  - [-] 8.2 Implementar `GET /reports/events` — listado paginado de eventos
    - Parámetros: `fecha_inicio` (req), `fecha_fin` (req), `id_estudiante` (opt), `id_ambiente` (opt), `page` (default 1), `page_size` (1-100, default 50)
    - Validar rango: si `fecha_fin - fecha_inicio > 90 días` → HTTP 400 `{"error": "rango-maximo-excedido"}`
    - Contar registros antes de retornar: si total > 10 000 → HTTP 400 `{"error": "resultado-excede-limite"}`
    - Si total = 0 → HTTP 200 con `{"data": [], "total": 0}`
    - Ordenar `timestamp_utc DESC`; responder dentro de 3000 ms para hasta 10 000 registros
    - _Requirements: 6.1, 6.4, 6.5, 6.6, 6.7_

  - [ ] 8.3 Implementar `GET /reports/attendance-summary` — resumen de asistencia
    - Parámetros: `id_estudiante` (req), `fecha_inicio` (req), `fecha_fin` (req)
    - Retornar total de accesos autorizados y denegados agrupados por `ambiente`
    - _Requirements: 6.2_

  - [ ]* 8.4 Escribir pruebas unitarias para Servicio_Reportes
    - Casos: rango válido con resultados, rango > 90 días, resultados > 10 000, lista vacía, resumen de asistencia
    - _Requirements: 6.1–6.7_

  - [ ]* 8.5 Escribir property test para Property 14: Reporte de eventos ordenado y paginado correctamente
    - **Property 14: Reporte de eventos ordenado y paginado correctamente**
    - **Validates: Requirements 6.1**

  - [ ]* 8.6 Escribir property test para Property 15: Validación del rango máximo de fechas en reportes
    - **Property 15: Validación del rango máximo de fechas en reportes**
    - **Validates: Requirements 6.4**

  - [ ]* 8.7 Escribir property test para Property 16: Resultado vacío y límite de resultados en reportes
    - **Property 16: Resultado vacío y límite de resultados en reportes**
    - **Validates: Requirements 6.6, 6.7**

- [ ] 9. Checkpoint — Servicio_Reportes
  - Ejecutar `pytest tests/unit/test_servicio_reportes.py tests/properties/test_properties_reportes.py`; asegurar que todos los tests pasen. Consultar al usuario si surgen dudas.

- [ ] 10. Middleware global de autorización basado en roles
  - [ ] 10.1 Implementar decorador `roles_required(*roles)` compartido entre microservicios
    - Verificar JWT con `jwt_required_with_revocation` (del paso 2.4); extraer claim `rol`
    - Si el rol no está en la lista de roles permitidos → HTTP 403
    - Aplicar a todos los endpoints del Servicio_Gestion (ADMINISTRADOR) y a endpoints de consulta del Servicio_Acceso y Servicio_Reportes (ADMINISTRADOR o AUXILIAR_EDUCACION)
    - _Requirements: 4.5, 4.6, 4.7, 4.8_

  - [ ]* 10.2 Escribir property test para Property 9: JWT inválido es rechazado por todos los endpoints protegidos
    - **Property 9: JWT inválido es rechazado por todos los endpoints protegidos**
    - **Validates: Requirements 4.4**

  - [ ]* 10.3 Escribir property test para Property 10: Control de acceso basado en roles es consistente
    - **Property 10: Control de acceso basado en roles es consistente**
    - **Validates: Requirements 4.5, 4.6, 4.7, 4.8**

  - [ ]* 10.4 Escribir property test para Property 11: Logout invalida el token para uso futuro
    - **Property 11: Logout invalida el token para uso futuro**
    - **Validates: Requirements 4.9**

- [ ] 11. Firmware ESP32
  - [ ] 11.1 Crear proyecto PlatformIO/Arduino para el firmware ESP32
    - Inicializar proyecto en `firmware/`; agregar dependencias: `MFRC522`, `ArduinoJson`, `WiFiClientSecure`, `Preferences` (NVS)
    - Definir `NodeConfig` struct en `config.h` con campos: `wifi_ssid`, `wifi_password`, `backend_url`, `node_id`, `node_token`, `timeout_ms=2000`, `max_retries=3`, `retry_interval_ms=5000`, `heartbeat_interval_s=60`
    - _Requirements: 3.1, 8.1_

  - [ ] 11.2 Implementar máquina de estados del firmware
    - Implementar estados: `Inicializando → Conectando_WiFi → Autenticando_Nodo → Operativo → Leyendo_RFID → Enviando_Evento → Procesando_Respuesta → Actuando_Resultado → Timeout_Local → Enviando_Heartbeat → Error_Auth → Esperando_Config`
    - Transiciones según diagrama de estados del diseño
    - _Requirements: 3.1, 3.3, 3.7, 8.1, 8.5, 8.6_

  - [ ] 11.3 Implementar lectura RFID y envío de evento al Servicio_Acceso
    - Al detectar tag con RC-522: componer JSON `{tag_rfid, node_id, timestamp_utc}` y realizar `POST /access/events` con cabecera `Authorization: Bearer <node_token>` dentro de 500 ms
    - Si respuesta `resultado = "autorizado"` → activar señal GPIO durante exactamente 3 s
    - Si no hay respuesta en 2000 ms → registrar localmente como "timeout"; no activar apertura
    - Si HTTP 401 → registrar "error-autenticacion"; no reintentar hasta nueva config
    - Si otro error HTTP → aplicar política de reintentos (máx 3, intervalo 5 s)
    - _Requirements: 3.1, 3.2, 3.3, 3.7, 8.1, 8.5, 8.6_

  - [ ] 11.4 Implementar heartbeat periódico cada 60 s
    - Usar `millis()` para disparar `POST /access/heartbeat` cada 60 000 ms con token de nodo
    - _Requirements: 3.9_

  - [ ]* 11.5 Escribir pruebas unitarias del firmware con mock HTTP (Unity)
    - Simular respuestas del Servicio_Acceso: 200 autorizado, 200 denegado, 401, timeout, 5xx (3 reintentos)
    - Verificar duración exacta de señal de apertura (3 s), comportamiento ante timeout, y registro local
    - _Requirements: 3.3, 3.7, 8.5, 8.6_

- [ ] 12. Frontend React.js (puerto 3000)
  - [ ] 12.1 Crear proyecto Vite + React 18 + TypeScript
    - Inicializar proyecto en `frontend/`; instalar dependencias: `react`, `react-dom`, `react-router-dom`, `axios`, `zustand` (o Redux Toolkit), `vitest`, `@testing-library/react`, `playwright`
    - Configurar `vite.config.ts` con proxy hacia el API Gateway (desarrollo local)
    - Crear `Dockerfile` de frontend: build Vite → servir con Nginx estático
    - _Requirements: 9.1_

  - [ ] 12.2 Implementar módulo de autenticación y protección de rutas
    - Crear `AuthContext` / store con JWT, rol y `primer_login`
    - Implementar `PrivateRoute` que redirige a `/login` si no hay token válido
    - Implementar guard de primer login: si `primer_login = true`, redirigir a `/change-password` y bloquear navegación a cualquier otra ruta; al intentar navegar, invalidar sesión y forzar logout
    - Implementar páginas `/login` y `/change-password` con formularios y llamadas a `POST /auth/login` y `POST /auth/change-password`
    - _Requirements: 4.1, 4.4, 7.5_

  - [ ] 12.3 Implementar hook `useAccessEvents` con SSE y panel de monitoreo en tiempo real
    - Crear `useAccessEvents.ts`: abrir `EventSource` a `/access/events/stream` con header JWT; al recibir evento llamar a store para actualizar lista
    - Crear componente `MonitoringDashboard`: tabla con columnas Estudiante, Ambiente, Timestamp (ISO 8601), Resultado; indicadores de estado de nodo (verde "En línea" / rojo "Sin conexión")
    - Asegurar actualización sin recarga de página en ≤ 3 s tras persistencia del evento
    - _Requirements: 5.1, 5.2, 5.4, 5.5_

  - [ ] 12.4 Implementar filtros de monitoreo con lógica AND
    - Agregar controles de filtro: Ambiente (select), fecha (date picker), resultado (select: todos/autorizado/denegado)
    - Aplicar filtros sobre la lista de eventos en el store; mostrar únicamente eventos que satisfacen simultáneamente todos los filtros activos
    - _Requirements: 5.3_

  - [ ] 12.5 Implementar módulos de gestión (ADMINISTRADOR)
    - Páginas CRUD para `/students`, `/environments`, `/nodes`, `/users`; llamar a endpoints de Servicio_Gestion
    - Mostrar errores de validación del backend (409, 422) con mensajes descriptivos en la UI
    - _Requirements: 1.1, 1.2, 2.1, 2.3, 7.1_

  - [ ] 12.6 Implementar módulo de reportes con exportación CSV
    - Página `/reports`: formulario con `fecha_inicio`, `fecha_fin`, `id_estudiante` (opt), `id_ambiente` (opt)
    - Mostrar tabla de resultados con paginación; botón "Exportar CSV" que genera y descarga archivo CSV UTF-8 delimitado por comas con ≤ 10 000 filas (cabecera + datos)
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ]* 12.7 Escribir pruebas unitarias del frontend con Vitest + React Testing Library
    - Casos: renderizado del dashboard con eventos SSE, aplicación de filtros AND, flujo de primer login (bloqueo de navegación), exportación CSV, manejo de errores HTTP del backend
    - _Requirements: 5.1–5.5, 6.3, 7.5_

  - [ ]* 12.8 Escribir property test para Property 17: Exportación CSV correctamente formateada
    - **Property 17: Exportación CSV correctamente formateada**
    - **Validates: Requirements 6.3**

  - [ ]* 12.9 Escribir property test para Property 18: Filtros de monitoreo con lógica AND estricta
    - **Property 18: Filtros de monitoreo con lógica AND estricta**
    - **Validates: Requirements 5.3**

- [ ] 13. Pruebas de integración
  - [ ] 13.1 Escribir prueba de integración SSE — latencia de eventos en tiempo real
    - En `tests/integration/test_sse_stream.py`: publicar evento de acceso vía `POST /access/events` y medir el tiempo hasta que el cliente SSE lo recibe; verificar ≤ 3 s
    - Verificar que el evento contiene: nombre del estudiante, nombre del ambiente, timestamp ISO 8601, resultado
    - _Requirements: 5.1, 5.2_

  - [ ] 13.2 Escribir prueba de integración de heartbeat y estado "sin-conexion"
    - En `tests/integration/test_node_heartbeat.py`: registrar un nodo, detener heartbeats y verificar que tras 120 s el estado cambia a "sin-conexion"; verificar que el evento SSE de tipo `node_status` se emite
    - _Requirements: 3.9, 5.4, 5.5_

  - [ ] 13.3 Escribir pruebas de smoke de infraestructura
    - En `tests/integration/test_docker_compose.py`: verificar que `docker-compose up` levanta todos los servicios con `/health` respondiendo HTTP 200
    - Verificar que bcrypt usa factor de coste ≥ 12
    - Verificar que el volumen de PostgreSQL persiste datos tras recrear el contenedor
    - _Requirements: 4.3, 9.1, 9.3, 9.4_

  - [ ]* 13.4 Escribir pruebas E2E con Playwright — flujo de acceso completo
    - En `tests/e2e/test_access_flow.py`: simular lectura RFID → envío de evento → verificar aparición en dashboard en ≤ 3 s
    - _Requirements: 5.1, 5.2_

  - [ ]* 13.5 Escribir pruebas E2E con Playwright — gestión administrativa
    - En `tests/e2e/test_admin_management.py`: flujo completo de creación de estudiante + asociación RFID + generación de reporte CSV
    - _Requirements: 1.1, 1.2, 6.3_

- [ ] 14. Checkpoint final — Suite completa de tests
  - Ejecutar `pytest tests/` con cobertura; verificar que Servicio_Autenticacion ≥ 90%, Servicio_Acceso ≥ 90%, Servicio_Gestion ≥ 85%, Servicio_Reportes ≥ 85%, Frontend ≥ 75%. Consultar al usuario si surgen dudas.

- [ ] 15. Configuración Nginx API Gateway y TLS
  - [ ] 15.1 Crear configuración Nginx como reverse proxy con rutas a microservicios
    - Crear `nginx/nginx.conf`: proxy `POST/GET /access/*` → `servicio-acceso:5002`, `/auth/*` → `servicio-autenticacion:5001`, `/management/*` → `servicio-gestion:5003`, `/reports/*` → `servicio-reportes:5004`, `/` → `frontend:3000`
    - Configurar header forwarding: `X-Forwarded-For`, `X-Real-IP`
    - _Requirements: 9.1_

  - [ ] 15.2 Configurar TLS y redirección HTTP → HTTPS en Nginx
    - Escuchar en el puerto 443 con certificado TLS; rechazar conexiones HTTP en puerto 80 con redirección 301 a HTTPS
    - Incluir `ssl_protocols TLSv1.2 TLSv1.3` y `ssl_ciphers` seguros
    - Agregar sección en `docker-compose.yml` para montar el certificado y la clave privada como secretos Docker
    - _Requirements: 8.4_

  - [ ] 15.3 Agregar health checks de Docker Compose para todos los servicios
    - Añadir bloque `healthcheck` en `docker-compose.yml` para cada microservicio usando su endpoint `/health`
    - Configurar `interval: 10s`, `timeout: 5s`, `retries: 3`, `start_period: 20s`
    - Verificar que `depends_on` de los microservicios use `condition: service_healthy` para PostgreSQL
    - _Requirements: 9.2, 9.3, 9.5, 9.6_

---

## Notes

- Las sub-tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea referencia requisitos específicos para trazabilidad completa
- Los checkpoints validan el progreso incremental antes de avanzar a la siguiente capa
- Las pruebas de propiedades usan Hypothesis con `@settings(max_examples=100)` y la etiqueta `# Feature: iot-rfid-access-control, Property N: <texto>`
- El diseño especifica Python 3.11 / Flask para todos los microservicios y TypeScript para el frontend
- El firmware ESP32 usa PlatformIO con las bibliotecas MFRC522 y ArduinoJson

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4"] },
    { "id": 2, "tasks": ["2.1", "4.1", "6.1", "8.1"] },
    { "id": 3, "tasks": ["2.2", "4.2", "6.2", "8.2"] },
    { "id": 4, "tasks": ["2.3", "4.3", "6.3", "8.3"] },
    { "id": 5, "tasks": ["2.4", "4.4", "6.4"] },
    { "id": 6, "tasks": ["2.5", "4.5", "6.5", "10.1"] },
    { "id": 7, "tasks": ["2.6", "4.6", "6.6", "8.4", "11.1"] },
    { "id": 8, "tasks": ["2.7", "2.8", "2.9", "4.7", "4.8", "4.9", "4.10", "6.7", "6.8", "6.9", "6.10", "8.5", "8.6", "8.7", "10.2", "10.3", "10.4", "11.2"] },
    { "id": 9, "tasks": ["11.3", "12.1"] },
    { "id": 10, "tasks": ["11.4", "12.2"] },
    { "id": 11, "tasks": ["11.5", "12.3"] },
    { "id": 12, "tasks": ["12.4", "12.5"] },
    { "id": 13, "tasks": ["12.6"] },
    { "id": 14, "tasks": ["12.7", "12.8", "12.9", "13.1", "13.2", "13.3"] },
    { "id": 15, "tasks": ["13.4", "13.5", "15.1"] },
    { "id": 16, "tasks": ["15.2"] },
    { "id": 17, "tasks": ["15.3"] }
  ]
}
```
