# Ejecución local — dev

## Requisitos

- Node.js 24 y Docker Engine/Desktop iniciado, con contenedores Linux.
- Docker Compose con soporte de `up --wait` (2.20 o superior; también Compose 5).
- Conexión a Internet para la primera construcción. MinIO se compila desde código fuente: reservar varios minutos y memoria para Go.
- No hace falta instalar Python ni PostgreSQL en el host. Arduino IDE y las bibliotecas del firmware se requieren solo para probar la electrónica.

## Primer arranque

Ejecutar desde la raíz del repositorio, tanto en PowerShell como en una terminal Linux:

```sh
node deploy/dev.mjs start
node deploy/dev.mjs admin
```

El primer comando genera `deploy/env/dev.env` con secretos aleatorios si no existe; preserva cualquier configuración existente. Construye imágenes, inicia PostgreSQL y MinIO, crea el bucket privado y su usuario de aplicación, aplica migraciones y arranca los servicios. El segundo solicita usuario, correo y contraseña del administrador de forma interactiva.

No editar `dev.env.example` para almacenar secretos. El archivo `dev.env` real está excluido de Git y no se copia a las imágenes.

| Servicio | Dirección local |
| --- | --- |
| Frontend | http://localhost:5173/et-talent-smart/ |
| Django admin | http://localhost:8000/admin/ |
| API disponible | http://localhost:8000/api/health/ready/ |
| Talentosito | http://localhost:8001/ |
| Panel y gateway RFID | http://localhost:3000/ |
| PostgreSQL / MinIO | Red privada de Compose, sin puertos publicados |

En el admin, crear cuentas con correo único, contraseña, rol y estado activo. Crear grados/secciones y cursos; asignar a los estudiantes su aula y llave RFID. El login del frontend utiliza el correo, aunque el superusuario tenga un nombre de usuario diferente.

Para datos de prueba, usar cuentas ficticias creadas en el admin o por la API. La suite de pruebas crea sus propios datos en una base temporal y no necesita poblar la base dev. No hay un usuario ni una contraseña de demostración incorporados.

## Configuración de voz y electrónica

Añadir `GROQ_API_KEY` a `deploy/env/dev.env` y volver a ejecutar `node deploy/dev.mjs compose up -d talentosito`. Sin esa clave, la salud y las pruebas simuladas funcionan, pero una consulta real de voz responde 503. Los modelos y voces pueden configurarse en el archivo privado; su disponibilidad y términos dependen del proveedor.

Copiar las plantillas de firmware a `secrets.h` en la misma carpeta que el sketch:

- RFID: `pagina-control/secrets.example.h`.
- Voz: `talentosito/secrets.example.h`.
- Prueba STT: `talentosito/esp32_stt_test/secrets.example.h`.

Completar Wi-Fi, IP LAN del equipo y `TALENTOSITO_DEVICE_KEY` para las pruebas de voz. Para RFID, completar `pagina-control/secrets.h` con `RFID_API_KEY` del mismo ambiente y las URLs del puerto 3000. No copiar claves de PostgreSQL, MinIO o Groq al dispositivo.

`pagina-control/` participa en este arranque. Su panel usa las cuentas de Django: administrador para crear estudiantes y asignar llaves; auxiliar para monitorear asistencia. Ver [su guía de firmware](../pagina-control/README.md).

Por defecto las API solo escuchan en loopback. Para el ESP32, configurar `DEV_BIND_IP=0.0.0.0`, añadir la IP LAN a `DJANGO_ALLOWED_HOSTS`, recrear backend/Talentosito/pagina-control y permitir 3000/8000/8001 en el firewall de la red local. El ESP32 debe estar en esa red. `localhost` en el ESP32 identifica al propio dispositivo, no al equipo.

Las rutas y cabeceras se describen en [api.md](api.md). La API valida el UID y registra la asistencia. El servo y sensor se controlan localmente en el firmware de `pagina-control/`; Django recibe telemetría de estado sin enviar órdenes físicas.

## Desarrollo y pruebas

```sh
node deploy/dev.mjs test
node deploy/dev.mjs logs backend talentosito
node deploy/dev.mjs compose ps
node deploy/dev.mjs compose exec backend python manage.py check
node deploy/dev.mjs compose exec backend python manage.py makemigrations
node deploy/dev.mjs compose exec backend python manage.py migrate
npm --prefix frontend run build
```

Las pruebas incluyen roles, sesiones expiradas, aislamiento de estudiantes, publicación de horarios, filtros, incidencias, RFID y voz sin llamadas al proveedor. `smoke_test` comprueba escritura/lectura/borrado contra el MinIO real con un objeto temporal único. El frontend y los servicios Python tienen recarga de código; los archivos públicos de pagina-control están montados en modo lectura y basta recargar el navegador; los cambios de dependencias requieren reconstrucción.

Si solo se necesita ejecutar pruebas unitarias de Django sin PostgreSQL iniciado:

```sh
node deploy/dev.mjs compose run --rm --no-deps -e DJANGO_SETTINGS_MODULE=config.settings.test backend python manage.py test
```

Este modo usa SQLite solo para pruebas unitarias, no como base del ambiente dev. El comando `test` del helper y CI usan PostgreSQL.

## Apagado y restablecimiento

```sh
node deploy/dev.mjs stop
```

El apagado elimina los contenedores del proyecto local y conserva sus volúmenes. Para borrar deliberadamente **todos los datos locales de prueba**, comprobar primero `node deploy/dev.mjs compose ps` y ejecutar, solo para dev:

```sh
node deploy/dev.mjs compose down --volumes
node deploy/dev.mjs start
node deploy/dev.mjs admin
```

Nunca usar este restablecimiento con el proyecto qa.

## Diagnóstico

- No conecta Docker: iniciar Docker Desktop y seleccionar contenedores Linux.
- Puerto ocupado: consultar el proceso propietario; ajustar únicamente los puertos de dev en Compose.
- Error de credenciales después de editar el archivo privado: las contraseñas de una base ya inicializada no cambian al editar variables. Rotarlas dentro del servicio o restablecer los datos locales conscientemente.
- 401 en voz: revisar `X-Device-Key`; 503 en voz: falta configuración Groq o falló el servicio escolar.
- 401 web: volver a iniciar sesión; los tokens vencen a las 8 horas.
- Error de CORS: el origen incluye esquema y puerto, pero no la ruta `/et-talent-smart/`.
- MinIO no disponible: revisar `logs minio minio-init`. El backend solo estará listo cuando exista el bucket privado.
