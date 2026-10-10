# Validación de la implementación

## Interfaces por rol y datos dev — 10 de octubre de 2026

- Carga `seed_dev` ejecutada en PostgreSQL dev: administrador, coordinador y cuentas de apoyo para docente, auxiliar, estudiantes y padre. Datos ficticios documentados en [ejecución dev](ejecucion-dev.md); sin sobrescribir el superusuario existente.
- 28 pruebas Django correctas, incluidas la exclusividad del coordinador para asignar grupos, directorios limitados por rol, unicidad de correo, publicación sin cruces de docentes, eventos sobre borradores y rechazo de la carga de prueba en qa. La carga repetida conserva contraseñas y borradores editados.
- 14 pruebas Talentosito correctas y comprobación real de archivos privados en PostgreSQL/MinIO correcta.
- TypeScript y compilación Vite correctos.
- Verificación en Edge sin ventana contra dev: creación/edición de cuentas y llaves, asignación de estudiante, curso/docente, guardado/publicación de horario, rechazo de superposición, evento extracurricular, retiro temprano, CSV, justificación, vistas de padre/estudiante y navegación móvil. Menús comprobados para los seis roles. Datos temporales de esos recorridos eliminados; datos dev solicitados conservados.
- Recarga del frontend en Docker sobre Windows comprobada con `CHOKIDAR_USEPOLLING`.

Los eventos se incorporan al horario semanal anual; no se implementó un calendario de eventos de fecha única. Notas, conducta y comunicados siguen fuera del alcance de CU-01 a CU-07. No se desplegó esta actualización en qa.

Verificaciones realizadas localmente el 8 de octubre de 2026:

| Comprobación | Resultado |
| --- | --- |
| Construcción de frontend, Django, Talentosito, MinIO y cliente MinIO | Correcta |
| Arranque dev con PostgreSQL y MinIO privados | Correcto; migraciones aplicadas y servicios disponibles |
| Pruebas Django sobre PostgreSQL | 10 pruebas correctas |
| Pruebas Talentosito con proveedor simulado | 14 pruebas correctas |
| Consistencia de migraciones | Sin cambios pendientes |
| TypeScript y compilación Vite | Correctos |
| Login y carga/descarga privada usando PostgreSQL y MinIO reales | Correctos; cuenta y metadatos temporales revertidos |
| Escritura, lectura y eliminación de objeto MinIO | Correctas |
| Configuración qa en proyecto local aislado | Correcta; puerto de prueba 19083, datos independientes de dev |
| Gateway qa: salud Django, admin, CSS y salud de voz | HTTP 200 |
| Voz sin clave a través del gateway | HTTP 401 |
| Exportación/importación de tar de un bucket vacío | Correcta; no equivale a una restauración de datos reales |
| Workflows con actionlint 1.7.7 | Sin errores; no se ejecutaron todavía en GitHub |
| Sintaxis Bash/sh de despliegue e inicialización | Correcta |
| Exclusión de configuración privada en Git | Verificada; plantillas versionables |

Entorno de verificación: Windows, Node.js 24.21, Docker Engine 29.8.1, Compose 5.5.1 y contenedores Linux con Python 3.12.

`check --deploy` no reportó errores. Conserva las advertencias W005/W021: no se fuerza HSTS sobre todos los subdominios ni la inclusión en listas de preload, ya que esa decisión requiere conocer el dominio definitivo y su infraestructura.

No se han validado todavía el servidor Hostinger real, los certificados/dominios de qa, un despliegue ejecutado por GitHub Actions, la restauración de un respaldo con datos institucionales, llamadas reales a Groq ni la operación en el ESP32 físico. Las guías [dev](ejecucion-dev.md) y [qa](despliegue-qa.md) indican cómo continuar estas verificaciones.

## Validación histórica del panel RFID — 9 de octubre de 2026

Estas comprobaciones corresponden al panel provisional, retirado después al definir iot como firmware IoT. Sus rutas e imagen ya no forman parte de la arquitectura vigente.

| Comprobación | Resultado |
| --- | --- |
| Migración 0003: eventos y estados RFID | Generada y aplicada en PostgreSQL dev; sin cambios de modelo pendientes |
| Django sobre PostgreSQL | 18 pruebas correctas: incluye reintentos entre días, llaves revocadas/reasignadas, permisos de auxiliar/administrador y telemetría independiente de asistencia |
| Talentosito | 14 pruebas correctas; proveedor simulado |
| MinIO y archivos privados | Escritura/lectura/borrado y API correctos; datos temporales revertidos |
| Imagen del panel provisional y arranque Compose dev | Correctos; panel disponible en localhost:3000 |
| Panel en Edge sin ventana | Creación de estudiante, búsqueda/asignación de llave, monitoreo del auxiliar, rechazo del rol estudiante y cierre de sesión correctos; cuentas temporales eliminadas |
| Configuración Compose qa | Válida con las cinco referencias de imágenes |
| Gateway qa probado localmente contra servicios dev | /rfid redirige a /rfid/; panel, JS, salud y proxy API responden 200; monitoreo sin sesión responde 401; secrets.h y database.json responden 404 |
| GitHub Actions y Bash | actionlint 1.7.7 y bash -n correctos |
| Compilación ESP32-C6 | Intentada, bloqueada por la instalación local del compilador; no se cargó firmware |

La prueba del gateway utilizó temporalmente el puerto local 19083 y se retiró su contenedor al terminar; no es un despliegue en Hostinger.

El intento inicial de compilación usó ESP32 Arduino 3.3.12, ArduinoJson 7.4.3, MFRC522 1.4.12 y ESP32Servo 3.2.1, con secretos de ejemplo y bibliotecas en un directorio temporal. El compilador no pudo ejecutar `cc1plus.exe` (`CreateProcess: No such file or directory`) de la herramienta `esp-rv32/2601`. Los resultados posteriores se detallan a continuación.

## Adaptación definitiva como capa IoT — 9 de octubre de 2026

Se retiraron el panel web, servidor, paquetes npm, JSON de prueba, Dockerfile y Nginx de iot. También se retiraron su servicio Compose, imagen de qa, rutas del gateway y contenedor local. El ESP32 utiliza directamente la API Django. La carpeta contiene el sketch, implementación C++, perfiles de pines, plantilla privada y guía del circuito.

| Comprobación | Resultado |
| --- | --- |
| ESP32 clásico (`esp32:esp32:esp32`) | Compilación correcta: 1 060 367 bytes de programa (80 %); 49 388 bytes de variables globales (15 %) |
| ESP32-C6 (`esp32:esp32:esp32c6`) | Compilación intentada; Windows bloqueó un proceso de la herramienta con error 4551: «Una directiva de Control de aplicaciones bloqueó este archivo» |
| Django / PostgreSQL | 18 pruebas correctas; migraciones consistentes |
| Talentosito | 14 pruebas correctas |
| MinIO y archivos privados | Comprobaciones correctas; datos de prueba revertidos |
| Compose dev / qa sin servicio RFID web | Configuraciones válidas; contenedor obsoleto retirado |
| GitHub Actions y Bash | actionlint 1.7.7 y bash -n sin errores |

La compilación utilizó Arduino ESP32 3.3.12 y las mismas bibliotecas del intento inicial, copiando los fuentes y secretos de ejemplo a una carpeta temporal. No se modificaron las políticas de Windows para evadir el bloqueo de C6. Falta completar esa compilación en un entorno autorizado y verificar ambas variantes en hardware; no se cargó firmware en ninguna placa.
