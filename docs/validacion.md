# Validación de la implementación

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

## Integración de pagina-control — 9 de octubre de 2026

| Comprobación | Resultado |
| --- | --- |
| Migración 0003: eventos y estados RFID | Generada y aplicada en PostgreSQL dev; sin cambios de modelo pendientes |
| Django sobre PostgreSQL | 18 pruebas correctas: incluye reintentos entre días, llaves revocadas/reasignadas, permisos de auxiliar/administrador y telemetría independiente de asistencia |
| Talentosito | 14 pruebas correctas; proveedor simulado |
| MinIO y archivos privados | Escritura/lectura/borrado y API correctos; datos temporales revertidos |
| Imagen pagina-control y arranque Compose dev | Correctos; panel disponible en localhost:3000 |
| Panel en Edge sin ventana | Creación de estudiante, búsqueda/asignación de llave, monitoreo del auxiliar, rechazo del rol estudiante y cierre de sesión correctos; cuentas temporales eliminadas |
| Configuración Compose qa | Válida con las cinco referencias de imágenes |
| Gateway qa probado localmente contra servicios dev | /rfid redirige a /rfid/; panel, JS, salud y proxy API responden 200; monitoreo sin sesión responde 401; secrets.h y database.json responden 404 |
| GitHub Actions y Bash | actionlint 1.7.7 y bash -n correctos |
| Compilación ESP32-C6 | Intentada, bloqueada por la instalación local del compilador; no se cargó firmware |

La prueba del gateway utilizó temporalmente el puerto local 19083 y se retiró su contenedor al terminar; no es un despliegue en Hostinger.

El intento de compilación usó ESP32 Arduino 3.3.12, ArduinoJson 7.4.3, MFRC522 1.4.12 y ESP32Servo 3.2.1, con secretos de ejemplo y bibliotecas en un directorio temporal. El compilador falló antes de validar el firmware: `riscv32-esp-elf-g++` no pudo ejecutar `cc1plus.exe` (`CreateProcess: No such file or directory`) de la herramienta `esp-rv32/2601`. Se requiere reparar esa instalación o compilar en un entorno Arduino funcional y luego verificar el lector, TLS, sensor y servo en la maqueta.
