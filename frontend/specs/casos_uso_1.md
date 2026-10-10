# Casos de uso nuevos — Talent Smart

## Propósito y alcance

Este documento complementa [features.md](features.md) con requisitos funcionales propuestos para la gestión de usuarios, horarios y asistencias. Los roles se definen en [info_usuarios.md](info_usuarios.md). Describe el comportamiento esperado; no implica que estas funciones estén implementadas. Las funciones de comunicados, conducta, notas y asistente descritas en ese archivo quedan fuera de estos casos de uso.

La implementación actual utiliza autenticación real y persistencia en Django/PostgreSQL. El frontend presenta menús y formularios por rol para estos casos; los permisos se validan también en el servidor. La guía [ejecución dev](../../docs/ejecucion-dev.md) incluye cuentas ficticias para comprobar los recorridos.

**Descripción breve del proyecto**: TalentSmart es un sistema tecnológico diseñado para modernizar la gestión escolar mediante la integración de la tecnología RFID y una aplicación web. Su objetivo es optimizar procesos como el registro de asistencia, la comunicación y la organización dentro de las instituciones educativas. Además, incorpora Talentosito, un asistente virtual que brinda apoyo, orientación y respuestas rápidas a estudiantes, docentes y padres de familia, haciendo que la experiencia educativa sea más eficiente, segura e innovadora.

## Actores

- **Administrador:** crea las cuentas de los usuarios y asigna las llaves o dispositivos RFID a los estudiantes.
- **Auxiliar de educación:** consulta las asistencias de todos los estudiantes o de un estudiante en particular, descarga reportes y registra los retiros tempranos.
- **Coordinador:** asigna grados y secciones a los estudiantes y cursos a los docentes; crea el horario anual de estudiantes y docentes, modifica sus bloques horarios y programa eventos extracurriculares para algunos grados y secciones o para todos.
- **Profesor o docente:** consulta y descarga asistencias de los estudiantes de sus cursos o materias y especifica las justificaciones o motivos de sus inasistencias.
- **Estudiante:** consulta su horario asignado y registra su asistencia diaria al colegio mediante su dispositivo RFID.
- **Padre de familia:** consulta la información de sus hijos, incluida su asistencia y permanencia en el colegio. Este rol no recibe permisos de gestión ni de descarga de reportes institucionales en estos casos.

El sistema debe aplicar permisos según el rol y las autorizaciones asignadas. La interfaz no debe ser el único control: cada operación protegida debe validarse también en el servidor.

La asistencia corresponde a la jornada escolar de cada estudiante, no a cada curso. La restricción del docente a sus cursos determina qué estudiantes puede consultar; no crea marcaciones de asistencia por materia.

## CU-01 — Iniciar sesión como personal institucional

**Actor principal:** administrador, coordinador, profesor o docente, o auxiliar de educación.

**Objetivo:** ingresar a las funcionalidades administrativas o de gestión permitidas para la cuenta.

**Precondiciones:** el administrador creó la cuenta institucional del usuario y esta se encuentra activa.

**Flujo principal:**

1. El usuario abre la opción de inicio de sesión.
2. Ingresa sus credenciales institucionales.
3. El sistema valida las credenciales y el estado de la cuenta.
4. El sistema identifica el rol y los permisos asociados.
5. El sistema muestra el panel y las acciones permitidas para ese usuario.

**Alternativas y excepciones:**

- Si las credenciales no son válidas, el acceso se rechaza y se muestra un mensaje sin revelar cuál dato falló.
- Si la cuenta está inactiva o no tiene permisos vigentes, el sistema deniega el acceso a las funciones protegidas.
- Si la sesión expira, el sistema solicita autenticación nuevamente antes de permitir operaciones protegidas.

**Reglas:** las credenciales no se almacenan en texto plano en el frontend. Las acciones administrativas quedan limitadas por permisos, no solo por ocultar opciones en pantalla.

## CU-02 — Registrar y publicar horarios

**Actor principal:** coordinador.

**Objetivo:** preparar y publicar el horario anual de los grados y secciones, con los cursos asignados a sus docentes y los tiempos de receso y almuerzo.

**Precondiciones:** el coordinador inició sesión; existen el año académico, los grados, las secciones, los cursos y los docentes correspondientes. Los estudiantes tienen grado y sección asignados y los cursos tienen docentes asignados por el coordinador.

**Flujo principal:**

1. El coordinador abre la gestión de horarios y selecciona el año académico, el grado y la sección.
2. El sistema presenta un molde de horario comprendido entre las **07:30 y las 16:30** (7:30 a. m. a 4:30 p. m.).
3. El coordinador distribuye los cursos en bloques por día, con hora de inicio y fin, docente y aula o espacio cuando corresponda.
4. Reserva bloques para recesos y almuerzo; puede ajustar las horas de los bloques dentro de la jornada del molde.
5. Cuando corresponda, incorpora eventos extracurriculares e indica los grados y secciones destinatarios o su aplicación a todos los estudiantes.
6. Guarda el horario como borrador o solicita publicarlo.
7. El sistema valida los datos y confirma el resultado.
8. Al publicarse, el horario queda disponible para los estudiantes del grado y sección y los docentes correspondientes.

**Alternativas y excepciones:**

- Si faltan datos obligatorios o la hora de fin no es posterior a la de inicio, el sistema señala los campos que deben corregirse.
- Si un bloque queda fuera del intervalo de 07:30 a 16:30, el sistema solicita ajustarlo antes de publicar.
- Si un bloque se superpone con otro del mismo destinatario, el sistema advierte el conflicto y evita publicar un horario inconsistente.
- Si el coordinador modifica un horario publicado, los cambios se guardan como borrador y la publicación vigente continúa visible hasta publicar la actualización.

**Reglas:** el horario se asigna por año académico, grado y sección. Cada bloque debe tener día, intervalo horario y tipo (curso, receso, almuerzo o evento extracurricular). Los bloques académicos se vinculan al curso y su docente; los demás tipos no exigen un curso. El molde delimita la jornada, pero no fija en este documento la duración de cada clase, receso o almuerzo. El sistema debe distinguir claramente borradores de horarios publicados y reemplazar la publicación vigente únicamente al publicar la actualización.

## CU-03 — Consultar horario personal

**Actor principal:** estudiante o docente.

**Objetivo:** consultar el horario publicado que corresponde al estudiante o docente.

**Precondiciones:** el usuario inició sesión; el estudiante tiene grado y sección asignados o el docente tiene cursos asignados.

**Flujo principal:**

1. El usuario abre la sección **Horarios**.
2. El sistema identifica el grado y sección del estudiante o los cursos asignados al docente.
3. Muestra el horario anual publicado vigente, organizado por día y hora dentro de la jornada de 07:30 a 16:30.
4. Cada bloque muestra su tipo y, cuando corresponda, curso, docente y aula o espacio. Se distinguen los recesos, el almuerzo y los eventos aplicables; para el docente se identifica también el grado y sección de sus clases.

**Alternativas y excepciones:**

- Si aún no hay un horario publicado, el sistema informa que no hay uno disponible.
- Si hay una actualización pendiente de publicación, el usuario continúa viendo el horario publicado vigente.

**Reglas:** el estudiante y el docente solo pueden consultar los horarios que les corresponden; no pueden modificarlos desde esta vista.

## CU-04 — Consultar y descargar reporte de asistencias

**Actor principal:** auxiliar de educación o profesor/docente.

**Objetivo:** revisar los registros de asistencia diaria al colegio y descargar un reporte.

**Precondiciones:** el usuario inició sesión y tiene permiso para consultar los estudiantes solicitados.

**Flujo principal:**

1. El usuario abre la sección de asistencias.
2. Selecciona un periodo de fechas (fecha inicial y final) y puede filtrar por grado, sección y estudiante en particular.
3. El sistema aplica los filtros dentro del alcance del usuario: todos los estudiantes para el auxiliar o únicamente estudiantes de los cursos o materias asignados al docente. Muestra los registros diarios y sus incidencias asociadas.
4. El usuario solicita descargar el reporte.
5. El sistema genera el archivo con los resultados filtrados e informa cuando la descarga está lista.

**Alternativas y excepciones:**

- Si no hay resultados para los criterios seleccionados, el sistema informa que el reporte está vacío y no presenta datos de otras consultas.
- Si la fecha final es anterior a la inicial o los filtros seleccionados son incompatibles, el sistema solicita corregirlos.
- Si la generación o descarga falla, el sistema informa el problema y permite volver a intentarlo.
- Si el usuario no tiene permiso para los criterios o los estudiantes solicitados, el sistema deniega esa consulta.

**Reglas:** el reporte debe corresponder a los filtros mostrados en pantalla y respetar los permisos del usuario. La unidad de asistencia es estudiante por día escolar; varias lecturas RFID no deben contabilizarse como varias asistencias del mismo día. El curso limita el acceso del docente, pero no es un filtro adicional del reporte. El formato de descarga y las columnas quedan por definir.

## CU-05 — Registrar falta justificada o retiro temprano

**Actor principal:** profesor/docente para justificar inasistencias de los estudiantes de sus cursos; auxiliar de educación para registrar retiros tempranos.

**Objetivo:** dejar constancia de una falta justificada o de un retiro temprano y su motivo.

**Precondiciones:** el usuario inició sesión, tiene permiso de registro y puede identificar al estudiante.

**Flujo principal:**

1. El usuario abre el formulario de incidencias de asistencia.
2. Busca y selecciona al estudiante.
3. Selecciona el tipo de incidencia permitido para su rol: falta justificada para el profesor/docente o retiro temprano para el auxiliar de educación.
4. Indica la fecha y, para un retiro temprano, la hora de salida.
5. Puede describir el motivo como información complementaria, sin exigir documentos de respaldo.
6. Confirma el registro.
7. El sistema valida los datos, guarda la incidencia y confirma su registro.

**Alternativas y excepciones:**

- Si falta un dato obligatorio o la fecha/hora no es válida, el sistema solicita corregirlo y no guarda el registro.
- Si ya existe un registro incompatible para el mismo estudiante y momento, el sistema advierte la posible duplicidad antes de guardar.
- Si el usuario no tiene permiso para ese estudiante, el sistema rechaza la operación.

**Reglas:** la incidencia debe quedar asociada al estudiante, tipo, fecha y usuario que la registró y, para retiros tempranos, a la hora de salida. No requiere adjuntos, justificantes documentales ni aprobación; queda registrada directamente tras validar los datos básicos. El motivo es opcional y no requiere un catálogo previo. La incidencia se vincula a la jornada del estudiante, no genera una asistencia separada por curso y no borra ni reemplaza el historial original ni las lecturas RFID.

## CU-06 — Crear cuentas y asignar llaves RFID

**Actor principal:** administrador.

**Objetivo:** crear las cuentas de los usuarios y vincular las llaves o dispositivos RFID de los estudiantes.

**Precondiciones:** el administrador inició sesión y dispone de los datos del usuario y, para asignar una llave, de su identificador RFID.

**Flujo principal:**

1. El administrador abre la gestión de usuarios.
2. Registra los datos de la cuenta y asigna el rol correspondiente según [info_usuarios.md](info_usuarios.md).
3. El sistema valida los datos y crea la cuenta institucional.
4. Para un estudiante, el administrador selecciona su cuenta y registra el identificador de la llave RFID que le asigna.
5. El sistema valida la vinculación, la guarda y confirma el resultado.

**Alternativas y excepciones:**

- Si faltan datos obligatorios o la cuenta ya existe, el sistema solicita corregirlos y evita crear una cuenta duplicada.
- Si la llave ya está asignada a otro estudiante, el sistema rechaza la asignación simultánea.
- Si el usuario no es administrador, el sistema deniega la creación de cuentas y la asignación de llaves.

**Reglas:** las cuentas son creadas por el administrador; no se contempla autorregistro. La llave identifica al estudiante para registrar asistencia y no sustituye las credenciales de acceso web. La asignación de grados y secciones corresponde al coordinador.

## CU-07 — Registrar asistencia diaria mediante el dispositivo

**Actor principal:** estudiante.

**Sistemas participantes:** lector/dispositivo RFID y backend RFID.

**Objetivo:** registrar la asistencia del estudiante al colegio para el día escolar correspondiente.

**Precondiciones:** el estudiante tiene una cuenta activa y una llave RFID asignada por el administrador; el lector puede comunicarse con el backend RFID. No se requiere una sesión web del estudiante para marcar asistencia.

**Flujo principal:**

1. El estudiante presenta su dispositivo o llave al lector RFID del colegio.
2. El lector envía la marcación al backend RFID.
3. El sistema valida la llave y su vinculación con un estudiante activo.
4. Guarda la lectura con el estudiante identificado y la fecha y hora de la marcación.
5. Registra la asistencia del estudiante para ese día escolar y confirma el resultado al dispositivo.
6. La asistencia queda disponible para las consultas y reportes autorizados.

**Alternativas y excepciones:**

- Si la llave es desconocida, no está asignada o pertenece a una cuenta inactiva, el sistema rechaza la marcación como asistencia.
- Si el estudiante vuelve a marcar el mismo día, se conserva la lectura sin duplicar su asistencia diaria.
- Si falla la comunicación o el almacenamiento, no se confirma una asistencia guardada; se informa el fallo para volver a intentarlo.

**Reglas:** la asistencia se mide por día de asistencia al colegio, no por curso. Las lecturas RFID originales se conservan separadas de las incidencias. La fecha escolar se determina con la zona horaria del colegio (America/Lima), para que marcaciones, consultas y reportes correspondan al mismo día local.

## Decisiones pendientes

- Definir el formato y las columnas del reporte descargable; los filtros ya son periodo de fechas, grado, sección y estudiante.
- Definir el calendario de días escolares, la hora de corte para tardanzas y cuándo se considera una falta por ausencia de marcación.
- Precisar las duraciones iniciales de los bloques del molde y cómo se resuelven eventos extracurriculares que sustituyen clases, manteniendo la jornada de 07:30 a 16:30.
- Definir si se conservarán versiones históricas de horarios además del borrador y la publicación vigente.
