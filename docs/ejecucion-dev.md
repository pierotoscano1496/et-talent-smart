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

El primer comando genera `deploy/env/dev.env` con secretos aleatorios si no existe; preserva cualquier configuración existente. Construye imágenes, inicia PostgreSQL y MinIO, crea el bucket privado y su usuario de aplicación, aplica migraciones, carga los datos de prueba de dev y arranca los servicios. El segundo es opcional: solicita usuario, correo y contraseña de un superusuario adicional de forma interactiva. El administrador demo ya permite iniciar sesión en la web.

### Inicialización SQL de la base de datos

En un volumen PostgreSQL vacío, la imagen oficial crea el usuario y la base definidos por `POSTGRES_USER`, `POSTGRES_PASSWORD` y `POSTGRES_DB`. Después, `start` ejecuta en este orden:

```sh
node deploy/dev.mjs compose run --rm --no-deps backend python manage.py migrate --noinput
node deploy/dev.mjs compose run --rm --no-deps backend python manage.py seed_dev
```

Las migraciones de Django ejecutan el SQL que crea y actualiza las tablas. Para inspeccionar el SQL de la migración inicial sin ejecutarlo:

```sh
node deploy/dev.mjs compose exec -T backend python manage.py sqlmigrate school 0001
```

`seed_dev` ejecuta el INSERT parametrizado de [dev_user.sql](../backend/school/sql/dev_user.sql) para cada cuenta documentada. Utiliza `ON CONFLICT (email) DO NOTHING` y genera el hash de la contraseña con Django antes de enviar los parámetros. Los grupos, cursos, vínculos familiares, horarios y asistencias se crean con el ORM en la misma transacción. El archivo SQL se ejecuta mediante el comando de Django, que proporciona sus parámetros; no se importa directamente con `psql`.

La carga ocurre después de las migraciones porque las tablas de la aplicación todavía no existen durante la inicialización del contenedor PostgreSQL. Los siguientes arranques completan los datos faltantes y conservan los existentes. No hace falta borrar los volúmenes ni crear la base manualmente.

No editar `dev.env.example` para almacenar secretos. El archivo `dev.env` real está excluido de Git y no se copia a las imágenes.

| Servicio | Dirección local |
| --- | --- |
| Frontend | http://localhost:5173/et-talent-smart/ |
| Django admin | http://localhost:8000/admin/ |
| API disponible | http://localhost:8000/api/health/ready/ |
| Talentosito | http://localhost:8001/ |
| PostgreSQL | `127.0.0.1:5432` |
| MinIO API S3 | http://localhost:9000/ |
| MinIO consola | http://localhost:9001/ |

### Inspección de PostgreSQL y MinIO

Para aplicar los puertos a un entorno dev que ya está iniciado, conservando sus datos:

```sh
node deploy/dev.mjs compose up -d --no-deps --wait postgres minio
```

Las credenciales están en el archivo privado `deploy/env/dev.env`:

- PostgreSQL (por ejemplo, desde DBeaver o pgAdmin): host `127.0.0.1`, puerto `5432`, base `POSTGRES_DB`, usuario `POSTGRES_USER` y contraseña `POSTGRES_PASSWORD`.
- Consola MinIO: abrir http://localhost:9001/ e ingresar con `MINIO_ROOT_USER` y `MINIO_ROOT_PASSWORD`.
- Cliente S3: endpoint `http://localhost:9000`, access key `MINIO_ACCESS_KEY`, secret key `MINIO_SECRET_KEY` y bucket `MINIO_BUCKET`; utilizar direccionamiento por ruta (path-style).

Estos puertos se publican únicamente en localhost para dev, incluso si `DEV_BIND_IP=0.0.0.0` permite conectar el ESP32 a las API. En qa, PostgreSQL y MinIO siguen sin puertos publicados. Los contenedores mantienen sus conexiones internas a `postgres:5432` y `minio:9000`.

Compose dev conecta también PostgreSQL y MinIO a la red `inspection` para permitir la publicación local de puertos; conservan su conexión a la red interna `data`.

En el admin, crear cuentas con correo único, contraseña, rol y estado activo. Crear grados/secciones y cursos; asignar a los estudiantes su aula y llave RFID. El login del frontend utiliza el correo, aunque el superusuario tenga un nombre de usuario diferente.

## Datos de prueba y acceso por rol

Con el entorno dev iniciado, ejecutar desde la raíz:

```sh
node deploy/dev.mjs seed
```

El comando crea estas cuentas ficticias. La contraseña inicial de todas las cuentas **nuevas** es `TalentDev!2026`:

| Correo | Rol / interfaz |
| --- | --- |
| `admin@demo.talentsmart.test` | Administrador: Usuarios, creación de cuentas y llaves RFID |
| `coordinador@demo.talentsmart.test` | Coordinador Pabel Valeriano: Grados y secciones, Cursos, Horarios y Eventos |
| `elvisp@demo.talentsmart.test` | Docente Elvis Perez: horario propio, asistencia de sus cursos, CSV y justificaciones |
| `afachin@escuelatalentos.edu.pe` | Docente Anthony Fachín: horario propio, asistencia de sus cursos, CSV y justificaciones |
| `cesar@demo.talentsmart.test` | Auxiliar César: asistencia general, CSV y retiros tempranos |
| `tliao@demo.talentsmart.test` | Estudiante Tomiko: horario y asistencia propios |
| `mtinco@demo.talentsmart.test` | Estudiante María: horario y asistencia propios |
| `alopez@escuelatalentos.edu.pe` | Estudiante Andrés: horario y asistencia propios |
| `alopez@gmail.com` | Padre de familia: asistencia de Andrés, su hijo vinculado |

Abrir http://localhost:5173/et-talent-smart/ e iniciar sesión con el correo. El administrador demo es una cuenta de aplicación: no es superusuario ni tiene acceso al admin de Django. El superusuario creado con `node deploy/dev.mjs admin` se conserva y también puede gestionar la web según su rol administrador.

La carga incluye los grupos 4 A y 4 B del año actual, los tres estudiantes en 4 A, un curso de Matemática a cargo de Elvis, un horario publicado con receso/almuerzo y una asistencia ficticia de Tomiko para el día actual. El padre está vinculado a Andrés. No asigna llaves RFID reales. Usa Usuarios para asignar una llave, Grados y secciones para cambiar el grupo y Horarios para editar/publicar los bloques.

Puede repetirse: conserva las cuentas existentes, sus contraseñas, nombres, asignaciones y horarios editados. Se ejecuta automáticamente con `start` y también puede invocarse con `seed`; no forma parte del despliegue de qa. Exige settings de desarrollo, `DEBUG=True` y `APP_ENV=dev`; en qa se rechaza. Las cuentas de una carga demo anterior se conservan; los nuevos correos se crean como cuentas adicionales. La suite de pruebas usa una base temporal independiente de estos datos.

## Configuración de voz y electrónica

Añadir `GROQ_API_KEY` a `deploy/env/dev.env` y volver a ejecutar `node deploy/dev.mjs compose up -d talentosito`. Sin esa clave, la salud y las pruebas simuladas funcionan, pero una consulta real de voz responde 503. Los modelos y voces pueden configurarse en el archivo privado; su disponibilidad y términos dependen del proveedor.

Copiar las plantillas de firmware a `secrets.h` en la misma carpeta que el sketch:

- RFID: `iot/secrets.example.h`.
- Voz: `talentosito/secrets.example.h`.
- Prueba STT: `talentosito/esp32_stt_test/secrets.example.h`.

Completar Wi-Fi, IP LAN del equipo y `TALENTOSITO_DEVICE_KEY` para las pruebas de voz. Para RFID, completar `iot/secrets.h` con `RFID_API_KEY` del mismo ambiente y las URLs de Django en el puerto 8000. No copiar claves de PostgreSQL, MinIO o Groq al dispositivo.

La capa IoT iot se compila y carga en el ESP32; no interviene en Compose. Las cuentas y llaves se gestionan en Django admin/API. Ver [circuito, pines y carga del firmware](../iot/README.md).

Por defecto las API solo escuchan en loopback. Para el ESP32, configurar `DEV_BIND_IP=0.0.0.0`, añadir la IP LAN a `DJANGO_ALLOWED_HOSTS`, recrear backend/Talentosito y permitir 8000/8001 en el firewall de la red local. El ESP32 debe estar en esa red. `localhost` en el ESP32 identifica al propio dispositivo, no al equipo.

Las rutas y cabeceras se describen en [api.md](api.md). La API valida el UID y registra la asistencia. El servo y sensor se controlan localmente en el firmware de `iot/`; Django recibe telemetría de estado sin enviar órdenes físicas.

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

Las pruebas incluyen roles, sesiones expiradas, aislamiento de estudiantes, publicación de horarios, filtros, incidencias, RFID y voz sin llamadas al proveedor. `smoke_test` comprueba escritura/lectura/borrado contra el MinIO real con un objeto temporal único. El frontend y los servicios Python tienen recarga de código; los cambios de dependencias requieren reconstrucción. Compose dev activa `CHOKIDAR_USEPOLLING` para que Vite detecte también los cambios de archivos montados desde Windows.

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
