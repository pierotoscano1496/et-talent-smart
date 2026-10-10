# API e integración electrónica

Base dev: `http://localhost:8000`. Base qa: `https://DOMINIO_API_QA`. Las rutas web terminan en `/`; la ruta de recepción RFID se define sin barra final. Este contrato es compartido por frontend, iot (RFID) y Talentosito (consultas). El ESP32 de iot se conecta directamente a estas rutas: puerto 8000 de la máquina en dev y dominio HTTPS del backend en qa. No existe gateway ni panel RFID separado.

## Autenticación y permisos

`POST /api/auth/login/` recibe `{"email":"usuario@institucion.edu","password":"..."}` y devuelve `token` y `user`. Las operaciones autenticadas envían `Authorization: Bearer TOKEN`. El token aleatorio se almacena hasheado en el servidor, caduca en 8 horas y se revoca con `POST /api/auth/logout/`. `GET /api/auth/me/` permite consultar la identidad.

No se usa autenticación por cookies en la API del navegador: Pages y Django pueden vivir en dominios diferentes. Las cookies y CSRF siguen aplicándose al admin de Django, servido desde el dominio de la API. CORS permite únicamente los orígenes configurados; no concede permisos.

| Ruta | Operación y alcance |
| --- | --- |
| `/api/users/` | Administrador: crear, listar, consultar y actualizar cuentas, estado y llaves |
| `/api/directory/` | Directorio mínimo sin credenciales ni RFID: coordinador consulta estudiantes/docentes; auxiliar/docente/estudiante/padre reciben solo los estudiantes de su alcance |
| `/api/classrooms/` | Coordinador: gestionar año, grado y sección |
| `/api/classrooms/ID/assign/` | Coordinador: POST con `student_id` para asignar estudiante |
| `/api/courses/` | Coordinador: nombre, aula/grupo (`classroom`) y docente (`teacher`) |
| `/api/schedules/` | Coordinador: crear/editar borradores |
| `/api/schedules/ID/publish/` | Coordinador: POST para validar y publicar |
| `/api/schedules/events/` | Coordinador: añadir un evento a los borradores de algunos grupos o todos los de un año |
| `/api/my-schedule/` | Estudiante/docente: publicaciones correspondientes |
| `/api/attendance/` | Consulta diaria según el alcance del usuario |
| `/api/attendance/export/` | Auxiliar/docente: CSV completo con los mismos filtros |
| `/api/incidents/` | Listar incidencias autorizadas; POST según tipo y rol |
| `/api/files/` | POST multipart con `file`; listar los archivos propios |
| `/api/files/ID/download/` | Descargar únicamente un archivo propio, previa autorización |
| `/api/health/live/` | Proceso disponible |
| `/api/health/ready/` | Base migrada y bucket MinIO accesibles |

Los listados paginados devuelven `count`, `next` y `results`, con páginas de 50. Los filtros son `start`, `end` (AAAA-MM-DD), `grade`, `section` y `student` (ID). El auxiliar consulta todos los estudiantes, el docente los de sus cursos, el estudiante su propia asistencia y el padre la de sus hijos vinculados. Administrador y coordinador no adquieren por su rol acceso a reportes de asistencia.

El CSV no se limita a las primeras 50 filas e incluye incidencias sin marcación. No calcula automáticamente tardanzas ni faltas por falta de lectura: las reglas del calendario y corte siguen pendientes. El frontend muestra por separado las marcaciones y las incidencias, indicando cuando hay más resultados.

Ejemplo de borrador:

```json
{
  "classroom": 1,
  "draft": [
    {"day": 0, "start": "07:30", "end": "09:00", "kind": "curso", "course_id": 1, "room": "Laboratorio"},
    {"day": 0, "start": "09:00", "end": "09:20", "kind": "receso"},
    {"day": 0, "start": "12:30", "end": "13:15", "kind": "almuerzo"}
  ]
}
```

`day` va de 0 (lunes) a 6 (domingo). Los bloques deben estar entre 07:30 y 16:30. Se aceptan borradores con superposiciones para su corrección, pero se rechaza su publicación. Editar un borrador no altera la publicación vigente. Los eventos usan `kind: "evento"` y `title`; se registran en el horario de cada grado/sección destinatario.

Las incidencias reciben `student`, `date`, `kind`, `reason` opcional y `exit_time` obligatorio solo para retiro temprano. El docente registra `falta_justificada`; el auxiliar registra `retiro_temprano`. El autor y la fecha de creación son del servidor. No hay adjuntos ni aprobación.

El directorio admite `search` por nombre y, para coordinadores, `role=estudiante` (por defecto) o `role=docente`. Devuelve identidad, rol, estado y grupo académico; no concede permisos para editar cuentas. La API de usuarios rechaza la asignación de `classroom`: corresponde al coordinador mediante `/api/classrooms/ID/assign/`. Los padres pueden vincular únicamente cuentas de estudiantes mediante `children`.

Los eventos reciben `year`, `classroom_ids` o `all_classrooms: true`, `day`, `start`, `end`, `title` y `room` opcional. Se incorporan como bloques del horario semanal anual, sin cambiar las publicaciones vigentes ni sustituir clases automáticamente. Deben revisarse y publicarse por grupo. Un evento idéntico ya presente no se añade otra vez. La publicación rechaza superposiciones dentro del grupo y entre clases publicadas del mismo docente en el mismo año.

## RFID

`POST /api/rfid/registro`, cabecera `X-API-KEY` configurada en el servidor y en el firmware:

```json
{"uid":"AABBCCDD","device_id":"ESP32C6_RFID_01","location_id":"PUERTA_PRINCIPAL","event_id":"boot-unico-1","wifi_rssi":-55,"millis":32000}
```

Se conserva cada lectura con hora del servidor y se consolida una asistencia por estudiante y día de America/Lima, mediante una restricción de unicidad en la base. Un UID desconocido/inactivo responde `authorized: false`. Una clave inválida se rechaza; ninguna de las dos situaciones registra asistencia.

`event_id` es opcional para compatibilidad; el firmware actual lo envía como identificador de arranque y secuencia. El par `device_id,event_id` es único: repetirlo devuelve la lectura original con `replayed: true` y no crea asistencia en otro día. Cambiar UID o ubicación del mismo evento devuelve 409. La respuesta incluye `ok`, `authorized`, `reading_id`, `attendance_date`, `attendance_created` y `usuario`. Una llave revocada o reasignada no vuelve a autorizar un evento anterior. Sin `event_id` se conserva cada solicitud como una lectura distinta, aunque sigue existiendo una sola asistencia diaria.

El firmware reintenta hasta tres veces con el mismo `event_id` ante errores de transporte, 408, 429 o 5xx. Errores definitivos (incluidos 4xx distintos de 408/429) no se reintentan. Si no recibe una respuesta autorizada válida, mantiene la puerta cerrada; no almacena lecturas offline.

- `GET /api/rfid/readings/`: auxiliar, últimas lecturas paginadas; filtro opcional `device_id`.
- `GET /api/rfid/summary/`: auxiliar, conteos del día de Lima: `readings`, `allowed`, `denied`, `attendance`.
- `GET /api/rfid/devices/`: administrador/auxiliar, último estado reportado por cada dispositivo con fecha del servidor.
- `POST /api/puerta/estado`: dispositivo con `X-API-KEY`; cuerpo `{"device_id":"ESP32C6_RFID_01","location_id":"PUERTA_PRINCIPAL","state":"abierta"}`. Estados: `abierta` o `cerrada`.
- `POST /api/puerta/cerrar`: compatibilidad, recibe los mismos identificadores y fuerza el estado reportado a `cerrada`.

Los reportes de puerta no marcan asistencia ni envían comandos al ESP32. Describen el último estado comandado por el firmware, no prueban posición física ni paso de una persona.

El administrador usa `/api/users/?role=estudiante&search=texto` para buscar cuentas y `PATCH /api/users/ID/` con `{"rfid_uid":"AABBCCDD"}` para asignar una llave; `null` la retira. Las llaves son únicas y se normalizan a mayúsculas. El auxiliar no puede modificar cuentas ni llaves. El navegador utiliza su sesión Bearer, nunca la clave del dispositivo.

## Talentosito

Dev: `http://IP_DEL_EQUIPO:8001`. Qa: `https://DOMINIO_API_QA/voice`.

- `POST /ask`: cuerpo WAV, cabecera `X-Device-Key`, respuesta PCM con `X-Audio-Sample-Rate`, `X-Audio-Bits` y `X-Audio-Channels`.
- `POST /transcribe`: mismo contrato de entrada, respuesta de texto.
- Máximo de audio: 4 MiB. Configurar en el cliente un timeout de hasta 180 segundos para el procesamiento completo; no reintentar automáticamente síntesis de voz en bucle.
- Una consulta sin `X-User-Token` es general: no tiene acceso a información personal.
- Para contexto personal, un cliente que ya tenga una sesión válida puede enviar `X-User-Token`. Talentosito lo valida contra Django usando su propia `X-Service-Key`; el backend devuelve solo identidad y horarios del usuario autenticado. El UID RFID o un parámetro `student_id` no sustituyen la sesión.
- El firmware actual envía únicamente la clave de dispositivo para consultas generales; el emparejamiento de una sesión web con un dispositivo personal requiere un flujo específico posterior.

La llamada interna usa `GET /api/talentosito/context/` con ambas credenciales. El timeout de consulta escolar es 10 segundos. Si la identidad falla se devuelve 403; si Django no responde, 503. No se envía una pregunta personal al modelo con un contexto de otro usuario ni se registran transcripciones o respuestas en los logs.

Las credenciales compartidas de RFID/voz son una primera configuración por ambiente. Su rotación exige actualizar servidor y dispositivos; no usar las mismas claves entre dev y qa.
