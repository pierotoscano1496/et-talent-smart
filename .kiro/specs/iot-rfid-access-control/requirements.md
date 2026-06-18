# Requirements Document

## Introduction

Sistema de control de ingreso de estudiantes a ambientes educativos mediante tecnología RFID. Cada nodo de acceso está compuesto por una placa ESP32 y un lector RC-522 que lee los tags RFID integrados en pulseras de los estudiantes. Los eventos de acceso se transmiten a un backend centralizado basado en microservicios Python/Flask, donde son persistidos en PostgreSQL y expuestos mediante una API REST. Una aplicación web React.js permite a Administradores gestionar usuarios y llaves RFID, y a Auxiliares de Educación monitorear el ingreso en tiempo real. La seguridad se gestiona mediante JWT con control de acceso basado en roles.

---

## Glossary

- **Sistema**: El sistema completo de control de acceso RFID IoT, incluyendo nodos físicos, backend y frontend.
- **Nodo_Acceso**: Unidad física compuesta por una placa ESP32 y un lector RC-522, instalada en la entrada de un ambiente educativo.
- **ESP32**: Microcontrolador con conectividad Wi-Fi/Bluetooth que actúa como controlador del nodo de acceso.
- **RC-522**: Módulo lector RFID de 13.56 MHz conectado al ESP32 para leer tags RFID.
- **Tag_RFID**: Identificador único de radiofrecuencia embebido en la pulsera del estudiante.
- **Pulsera**: Accesorio wearable que porta el estudiante y que contiene el Tag_RFID.
- **Estudiante**: Usuario del sistema que porta una Pulsera con Tag_RFID para acceder a los ambientes.
- **Administrador**: Usuario del sistema con privilegios para registrar y gestionar usuarios y llaves RFID.
- **Auxiliar_Educacion**: Usuario del sistema con acceso de solo lectura para monitorear el ingreso de estudiantes.
- **Ambiente**: Espacio físico educativo (aula, laboratorio, biblioteca, etc.) controlado por un Nodo_Acceso.
- **API_REST**: Interfaz de programación de aplicaciones bajo arquitectura REST expuesta por el Backend.
- **Backend**: Conjunto de microservicios implementados en Python/Flask que procesan la lógica de negocio.
- **Frontend**: Aplicación web desarrollada en React.js + Vite que provee la interfaz de gestión y monitoreo.
- **Base_Datos**: Sistema de gestión de base de datos PostgreSQL que persiste todos los datos del sistema.
- **JWT**: JSON Web Token utilizado para autenticar y autorizar solicitudes entre componentes del sistema.
- **Evento_Acceso**: Registro generado cada vez que un Tag_RFID es leído por un Nodo_Acceso, incluyendo identificador del tag, identificador del nodo, timestamp y resultado (autorizado/denegado).
- **Rol**: Nivel de privilegio asignado a un usuario del sistema (Administrador, Auxiliar_Educacion).
- **Servicio_Autenticacion**: Microservicio responsable de validar credenciales y emitir tokens JWT.
- **Servicio_Acceso**: Microservicio responsable de procesar los eventos de acceso provenientes de los Nodos_Acceso.
- **Servicio_Gestion**: Microservicio responsable de la gestión CRUD de usuarios, ambientes y llaves RFID.
- **Servicio_Reportes**: Microservicio responsable de consultar y agregar Eventos_Acceso para generar reportes.

---

## Requirements

### Requirement 1: Registro de Estudiantes y Llaves RFID

**User Story:** Como Administrador, quiero registrar estudiantes y asociar sus pulseras RFID, para que el sistema pueda identificarlos y controlar su acceso a los ambientes.

#### Acceptance Criteria

1. THE Servicio_Gestion SHALL exponer un endpoint POST que acepte nombre completo (máximo 100 caracteres), código de estudiante (alfanumérico, máximo 20 caracteres), grado/sección (máximo 20 caracteres) y persista el registro con estado activo por defecto.
2. THE Servicio_Gestion SHALL exponer un endpoint para asociar un Tag_RFID (cadena hexadecimal de 8 caracteres) a un Estudiante registrado.
3. WHEN un Administrador envía una solicitud de registro con un código de estudiante ya existente en la Base_Datos, THEN THE Servicio_Gestion SHALL retornar HTTP 409 con un cuerpo JSON que contenga el campo "error" con valor "codigo-duplicado".
4. WHEN un Administrador envía una solicitud de asociación con un Tag_RFID que ya está asignado a otro Estudiante activo o inactivo, THEN THE Servicio_Gestion SHALL retornar HTTP 409 con un cuerpo JSON que contenga el campo "error" con valor "tag-en-uso".
5. WHEN un Administrador envía una solicitud de desactivación para un Estudiante, THE Servicio_Gestion SHALL actualizar el campo estado del Estudiante a inactivo y retornar HTTP 200.
6. WHEN se desactiva un Estudiante, THE Servicio_Gestion SHALL conservar todos los Eventos_Acceso previamente asociados a ese Estudiante sin modificarlos.
7. WHEN un Administrador envía una solicitud de actualización para un Estudiante existente con campos nombre completo, grado/sección o estado, THEN THE Servicio_Gestion SHALL actualizar únicamente los campos enviados y conservar la asociación de Tag_RFID existente.

---

### Requirement 2: Gestión de Ambientes y Nodos de Acceso

**User Story:** Como Administrador, quiero registrar y configurar los ambientes educativos y sus nodos de acceso, para que el sistema reconozca qué nodo controla qué ambiente.

#### Acceptance Criteria

1. THE Servicio_Gestion SHALL exponer un endpoint POST que acepte nombre (cadena, máximo 80 caracteres), descripción (cadena, máximo 255 caracteres), ubicación (cadena, máximo 120 caracteres) y estado ("activo" o "inactivo") para crear un registro de Ambiente.
2. WHEN un Administrador intenta crear un Ambiente con un nombre que ya existe en la Base_Datos, THEN THE Servicio_Gestion SHALL retornar HTTP 409 con un cuerpo JSON que contenga el campo "error" con valor "nombre-ambiente-duplicado".
3. THE Servicio_Gestion SHALL exponer un endpoint POST que acepte identificador único (alfanumérico, máximo 40 caracteres), descripción (cadena, máximo 255 caracteres) y id_ambiente existente para registrar un Nodo_Acceso.
4. WHEN un Administrador intenta registrar un Nodo_Acceso con un identificador ya existente, THEN THE Servicio_Gestion SHALL retornar HTTP 409 con un cuerpo JSON que contenga el campo "error" con valor "identificador-nodo-duplicado".
5. WHEN un Administrador intenta registrar un Nodo_Acceso con un id_ambiente que no existe en la Base_Datos, THEN THE Servicio_Gestion SHALL retornar HTTP 422 con un cuerpo JSON que contenga el campo "error" con valor "ambiente-no-encontrado".
6. WHEN un Administrador envía una solicitud para habilitar o deshabilitar un Nodo_Acceso, THE Servicio_Gestion SHALL actualizar el campo estado del nodo y retornar HTTP 200, sin eliminar ningún Evento_Acceso previamente asociado.
7. WHILE un Nodo_Acceso tiene estado "inactivo", THE Servicio_Acceso SHALL denegar todos los intentos de acceso reportados por ese nodo y registrar el Evento_Acceso con resultado "denegado" y código_resultado "nodo-inactivo".

---

### Requirement 3: Control de Acceso en el Nodo Físico

**User Story:** Como Estudiante, quiero acercar mi pulsera RFID al lector del ambiente, para que el sistema registre mi ingreso y me permita el acceso si estoy autorizado.

#### Acceptance Criteria

1. WHEN el RC-522 detecta un Tag_RFID, THE ESP32 SHALL transmitir el identificador del tag, el identificador del Nodo_Acceso y el timestamp UTC al Servicio_Acceso mediante una solicitud HTTP POST dentro de los 500 ms siguientes a la lectura.
2. WHEN el Servicio_Acceso recibe una solicitud válida de Evento_Acceso, THE Servicio_Acceso SHALL retornar una respuesta HTTP al ESP32 dentro de los 1000 ms siguientes a la recepción.
3. WHEN el Servicio_Acceso retorna una respuesta de autorización, THE ESP32 SHALL activar la señal de apertura del mecanismo de acceso físico durante exactamente 3 segundos.
4. WHEN el Servicio_Acceso recibe un Evento_Acceso con un Tag_RFID asociado a un Estudiante activo, THEN THE Servicio_Acceso SHALL retornar HTTP 200 con campo "resultado" igual a "autorizado".
5. WHEN el Servicio_Acceso recibe un Evento_Acceso con un Tag_RFID no registrado, THEN THE Servicio_Acceso SHALL retornar HTTP 200 con campo "resultado" igual a "denegado" y campo "codigo_resultado" igual a "tag-no-registrado".
6. WHEN el Servicio_Acceso recibe un Evento_Acceso con un Tag_RFID asociado a un Estudiante inactivo, THEN THE Servicio_Acceso SHALL retornar HTTP 200 con campo "resultado" igual a "denegado" y campo "codigo_resultado" igual a "estudiante-inactivo".
7. IF el ESP32 no recibe respuesta del Servicio_Acceso dentro de los 2000 ms posteriores al envío, THEN THE ESP32 SHALL registrar el intento localmente con estado "timeout" y no activar la señal de apertura.
8. THE Servicio_Acceso SHALL persistir cada Evento_Acceso en la Base_Datos con los campos: id, tag_rfid, id_nodo, id_ambiente, timestamp_utc, resultado y codigo_resultado.
9. WHILE el Nodo_Acceso está operativo, THE ESP32 SHALL enviar un heartbeat HTTP al Servicio_Acceso cada 60 segundos; IF el Servicio_Acceso no recibe heartbeat de un Nodo_Acceso durante más de 120 segundos, THEN THE Servicio_Acceso SHALL actualizar el estado de conectividad de ese nodo a "sin-conexion" en la Base_Datos.

---

### Requirement 4: Autenticación y Autorización de Usuarios Web

**User Story:** Como usuario del sistema web (Administrador o Auxiliar_Educacion), quiero autenticarme con mis credenciales, para que el sistema verifique mi identidad y me otorgue acceso solo a las funcionalidades correspondientes a mi rol.

#### Acceptance Criteria

1. WHEN un usuario envía credenciales correctas al endpoint de inicio de sesión, THE Servicio_Autenticacion SHALL retornar HTTP 200 con un JWT firmado (HS256 mínimo) que incluya los claims: sub (id de usuario), rol (valor del Rol asignado) y exp (timestamp de expiración en 8 horas desde la emisión).
2. WHEN un usuario proporciona credenciales incorrectas, THEN THE Servicio_Autenticacion SHALL retornar HTTP 401 con mensaje genérico "credenciales-invalidas" sin indicar cuál campo es incorrecto.
3. THE Servicio_Autenticacion SHALL almacenar las contraseñas usando bcrypt con factor de coste mínimo 12.
4. WHEN un JWT recibido en cualquier endpoint protegido del Backend ha expirado, tiene firma inválida, o está en la lista de tokens revocados, THEN THE Backend SHALL retornar HTTP 401 y rechazar la solicitud sin procesar la acción solicitada.
5. WHILE un usuario autenticado posee Rol "ADMINISTRADOR" en el JWT, THE Backend SHALL permitir el acceso a los endpoints de creación, modificación y eliminación de recursos del Servicio_Gestion.
6. IF un usuario con Rol distinto a "ADMINISTRADOR" intenta acceder a un endpoint de creación, modificación o eliminación del Servicio_Gestion, THEN THE Backend SHALL retornar HTTP 403.
7. WHILE un usuario autenticado posee Rol "AUXILIAR_EDUCACION" en el JWT, THE Backend SHALL permitir el acceso únicamente a los endpoints de consulta del Servicio_Acceso y Servicio_Reportes.
8. IF un usuario con Rol "AUXILIAR_EDUCACION" intenta acceder a un endpoint fuera de los endpoints de consulta del Servicio_Acceso y Servicio_Reportes, THEN THE Backend SHALL retornar HTTP 403.
9. WHEN un usuario autenticado envía una solicitud al endpoint de cierre de sesión, THE Servicio_Autenticacion SHALL agregar el JWT a la lista de tokens revocados en la Base_Datos y retornar HTTP 200 con campo "mensaje" igual a "sesion-cerrada".

---

### Requirement 5: Monitoreo en Tiempo Real del Ingreso

**User Story:** Como Auxiliar_Educacion, quiero visualizar en tiempo real el ingreso de estudiantes a los diferentes ambientes, para que pueda supervisar la asistencia sin necesidad de presencia física.

#### Acceptance Criteria

1. WHEN un Evento_Acceso es persistido en la Base_Datos, THE Frontend SHALL actualizar el panel de monitoreo sin recargar la página dentro de los 3 segundos siguientes a la persistencia del evento.
2. WHEN se produce un Evento_Acceso, THE Frontend SHALL mostrar el nombre del Estudiante, el nombre del Ambiente, el timestamp en formato ISO 8601 y el resultado del acceso ("autorizado" o "denegado").
3. WHEN un Auxiliar_Educacion aplica filtros simultáneos por Ambiente, fecha y resultado, THE Frontend SHALL mostrar únicamente los Eventos_Acceso que satisfacen todos los filtros aplicados de forma conjunta (lógica AND).
4. WHEN el Servicio_Acceso actualiza el estado de conectividad de un Nodo_Acceso a "sin-conexion", THE Frontend SHALL mostrar un indicador visual de color rojo con el texto "Sin conexión" junto al nombre del nodo dentro de los 3 segundos siguientes a la actualización.
5. THE Frontend SHALL mostrar el estado de conectividad de cada Nodo_Acceso registrado, actualizando el indicador de "sin-conexion" a "en-linea" (color verde) dentro de los 3 segundos siguientes a la recepción de un heartbeat exitoso del nodo.

---

### Requirement 6: Generación de Reportes de Asistencia

**User Story:** Como Administrador, quiero generar reportes de asistencia por estudiante, ambiente y rango de fechas, para que pueda analizar los patrones de ingreso y tomar decisiones administrativas.

#### Acceptance Criteria

1. WHEN el Administrador solicita el reporte de Eventos_Acceso con los parámetros requeridos fecha_inicio y fecha_fin (y opcionalmente id_estudiante e id_ambiente), THE Servicio_Reportes SHALL retornar HTTP 200 con los registros ordenados del más reciente al más antiguo, paginados con máximo 100 registros por página.
2. WHEN el Administrador solicita un resumen de asistencia con parámetros requeridos id_estudiante, fecha_inicio y fecha_fin, THE Servicio_Reportes SHALL retornar HTTP 200 con el total de ingresos autorizados y denegados agrupados por Ambiente.
3. WHEN el Administrador solicita exportar el reporte de Eventos_Acceso, THE Frontend SHALL generar y descargar un archivo CSV con codificación UTF-8, delimitado por comas, con máximo 10 000 filas, correspondiente a los registros del filtro activo.
4. WHEN el rango entre fecha_inicio y fecha_fin supera los 90 días, THEN THE Servicio_Reportes SHALL retornar HTTP 400 con campo "error" igual a "rango-maximo-excedido".
5. WHEN el resultado de una consulta de reporte contiene entre 1 y 10 000 registros, THE Servicio_Reportes SHALL retornar la respuesta dentro de los 3000 ms siguientes a la recepción de la solicitud.
6. WHEN el resultado de una consulta de reporte no contiene registros que coincidan con los filtros aplicados, THE Servicio_Reportes SHALL retornar HTTP 200 con una lista vacía y el campo "total" igual a 0.
7. WHEN el resultado de una consulta de reporte supera los 10 000 registros, THEN THE Servicio_Reportes SHALL retornar HTTP 400 con campo "error" igual a "resultado-excede-limite" indicando al usuario que aplique filtros más restrictivos.

---

### Requirement 7: Gestión de Roles y Usuarios del Sistema Web

**User Story:** Como Administrador, quiero crear y gestionar las cuentas de los usuarios del sistema web (Administradores y Auxiliares de Educación), para que solo el personal autorizado tenga acceso a la plataforma.

#### Acceptance Criteria

1. THE Servicio_Gestion SHALL exponer un endpoint POST para que un Administrador cree una cuenta de usuario web con campos nombre completo, correo electrónico, contraseña temporal y Rol asignado ("ADMINISTRADOR" o "AUXILIAR_EDUCACION").
2. WHEN un Administrador intenta crear un usuario web con un correo electrónico ya registrado, THEN THE Servicio_Gestion SHALL retornar HTTP 409 con campo "error" igual a "email-duplicado".
3. WHEN un Administrador envía una solicitud para cambiar el Rol de un usuario web existente, THE Servicio_Gestion SHALL actualizar el campo rol del usuario y retornar HTTP 200, conservando intacto el historial de actividad del usuario.
4. WHEN un Administrador envía una solicitud para desactivar una cuenta de usuario web, THE Servicio_Gestion SHALL actualizar el campo estado del usuario a inactivo y THE Servicio_Autenticacion SHALL rechazar con HTTP 401 cualquier intento de inicio de sesión de ese usuario mientras esté inactivo.
5. WHEN un usuario web inicia sesión por primera vez con una contraseña temporal, THE Frontend SHALL redirigir al usuario al flujo de cambio de contraseña antes de permitir el acceso a cualquier otra funcionalidad; IF el usuario intenta navegar a otra ruta antes de completar el cambio, THEN THE Frontend SHALL bloquear la navegación, invalidar la sesión activa y cerrar la sesión del usuario forzosamente.

---

### Requirement 8: Comunicación Segura entre Nodos y Backend

**User Story:** Como Administrador, quiero que la comunicación entre los nodos ESP32 y el backend esté autenticada, para que no se puedan inyectar eventos de acceso falsos al sistema.

#### Acceptance Criteria

1. THE ESP32 SHALL incluir el token de autenticación de nodo en la cabecera HTTP `Authorization: Bearer <token>` de cada solicitud enviada al Servicio_Acceso; THE Servicio_Acceso SHALL rechazar solicitudes donde el token esté ausente, sea malformado o haya sido revocado.
2. WHEN el Servicio_Acceso recibe una solicitud con token ausente, malformado o revocado, THEN THE Servicio_Acceso SHALL retornar HTTP 401, registrar en la bitácora de seguridad el timestamp, el identificador del nodo (si identificable) y el motivo del rechazo, y descartar la solicitud sin persistir ningún Evento_Acceso.
3. THE Servicio_Gestion SHALL exponer endpoints para que el Administrador genere, revoque y regenere el token de autenticación de cada Nodo_Acceso; WHEN se ejecuta cualquiera de estas operaciones, THE Servicio_Gestion SHALL retornar HTTP 200 con el estado actualizado del token.
4. THE Backend SHALL transmitir todas las comunicaciones externas exclusivamente sobre HTTPS con certificado TLS emitido por una autoridad certificadora reconocida; conexiones sobre HTTP plano SHALL ser rechazadas con redirección 301 a HTTPS.
5. IF el ESP32 recibe HTTP 401 del Servicio_Acceso, THEN THE ESP32 SHALL registrar el evento localmente con estado "error-autenticacion" y no reintentar la solicitud hasta recibir una nueva configuración de token desde el Servicio_Gestion.
6. IF el ESP32 recibe un código de respuesta HTTP distinto a 401 y distinto a 2xx del Servicio_Acceso, THEN THE ESP32 SHALL registrar el evento localmente con el código de respuesta recibido y aplicar la política de reintentos configurada (máximo 3 reintentos con intervalo de 5 segundos).

---

### Requirement 9: Despliegue y Disponibilidad del Sistema

**User Story:** Como Administrador, quiero que el sistema esté disponible de manera continua y sea desplegable mediante contenedores Docker, para que el mantenimiento y las actualizaciones no interrumpan el servicio educativo.

#### Acceptance Criteria

1. THE Sistema SHALL empaquetar cada microservicio del Backend, el Frontend y la Base_Datos en imágenes Docker independientes orquestadas mediante un archivo docker-compose.yml en la raíz del repositorio.
2. THE Sistema SHALL mantener una disponibilidad operativa del 99% medida en ventanas de 30 días, excluyendo ventanas de mantenimiento programadas notificadas con al menos 24 horas de anticipación.
3. WHEN un microservicio del Backend falla y su contenedor se reinicia, THE Sistema SHALL restablecer el estado operativo del microservicio —definido como el endpoint `/health` respondiendo HTTP 200 y el servicio procesando solicitudes sin error— dentro de los 30 segundos siguientes al reinicio del contenedor.
4. THE Sistema SHALL persistir los datos de la Base_Datos en un volumen Docker externo al contenedor, de modo que un reinicio o recreación del contenedor no resulte en pérdida de datos.
5. IF el servicio de Base_Datos no está disponible, THEN THE Backend SHALL retornar HTTP 503 a todas las solicitudes entrantes, incluyendo el endpoint `/health`; WHEN una verificación de salud interna confirme que la conexión con la Base_Datos ha sido restablecida, THE Backend SHALL reanudar respuestas normales dentro de los 10 segundos siguientes.
6. IF un contenedor de microservicio falla 3 veces consecutivas al intentar iniciarse, THEN THE Sistema SHALL registrar el evento en el log de orquestación con timestamp y nombre del servicio, y mantener los demás microservicios operativos sin interrupción.
