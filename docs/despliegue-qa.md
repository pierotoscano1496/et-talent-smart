# Despliegue de qa — GitHub Pages y Hostinger

## Preparación del servidor

Esta guía presupone un VPS Hostinger Linux con Docker Engine y Compose (2.20+), Bash, Python 3, `flock`, `ss`, acceso SSH y permisos para ejecutar Docker. El hosting compartido sin Docker no satisface esta arquitectura.

Antes de instalar o publicar, inspeccionar los servicios existentes:

```sh
docker ps --format 'table {{.Names}}\t{{.Ports}}'
ss -ltn
```

Los puertos **9082, 4567 y 3307 están reservados al otro servicio**. Verificar que 9083 está libre; si no, seleccionar otro mediante `QA_HTTP_PORT` y ajustar el proxy. No detener servicios ajenos para liberar un puerto.

Configurar un usuario de despliegue con acceso a Docker y un directorio propio `/opt/talentsmart`, con subdirectorios `releases` y `backups`. El acceso a Docker equivale a privilegios elevados sobre ese host: usar una cuenta dedicada. Mantener acceso al archivo de configuración restringido a esa cuenta.

Crear `/etc/talentsmart/qa.env` copiando `deploy/env/qa.env.example`. Generar un secreto diferente para cada variable con `openssl rand -hex 40`, completar dominios y configurar permisos 600. No guardar este archivo en el checkout ni en Actions como artefacto.

La contraseña inicial de PostgreSQL se aplica al crear su volumen: para rotarla después se requiere cambiarla también dentro de la base. Las claves raíz de MinIO solo se entregan a MinIO y a su inicializador; Django usa la identidad limitada al bucket privado.

## Dominio y HTTPS

El proxy existente está en el host: `/etc/nginx/sites-available/chambita-api-qa` dirige Chambita a `127.0.0.1:9082`. Talent Smart utiliza un sitio independiente y `127.0.0.1:9083`. Nginx comparte 80/443 entre dominios mediante `server_name`.

1. En la zona DNS de `vexaperu.com`, crear un registro A con nombre `api-talentsmart-qa` y valor igual a la IP pública del VPS. Si existe un AAAA, debe apuntar al IPv6 correcto del mismo servidor.
2. Comprobar que el dominio resuelve al VPS y que HTTP 80 y HTTPS 443 están permitidos en los firewalls.
3. Copiar `deploy/nginx/host-http.example.conf` al VPS como `/tmp/talentsmart-api-qa.conf`. Esta plantilla HTTP permite emitir el primer certificado sin referenciar archivos TLS inexistentes.
4. En el VPS, ejecutar:

```sh
sudo install -m 644 /tmp/talentsmart-api-qa.conf /etc/nginx/sites-available/talentsmart-api-qa
sudo ln -s /etc/nginx/sites-available/talentsmart-api-qa /etc/nginx/sites-enabled/talentsmart-api-qa
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d api-talentsmart-qa.vexaperu.com --redirect
sudo nginx -t && sudo systemctl reload nginx
sudo certbot renew --dry-run --cert-name api-talentsmart-qa.vexaperu.com
```

Crear el enlace únicamente si no existe. Certbot modifica el sitio para instalar HTTPS y la redirección. `host.example.conf` sirve como referencia del resultado final, después de emitir el certificado; no hace falta reemplazar el sitio generado por Certbot.

Antes de levantar el gateway, la ruta de aplicación puede responder 502; esto no impide el challenge de Certbot. Tras el despliegue, comprobar `https://api-talentsmart-qa.vexaperu.com/api/health/ready/`.

En `/etc/talentsmart/qa.env`, usar `DJANGO_ALLOWED_HOSTS=api-talentsmart-qa.vexaperu.com,localhost,127.0.0.1,backend`, `CSRF_TRUSTED_ORIGINS=https://api-talentsmart-qa.vexaperu.com` y `QA_HTTP_PORT=9083`. En los entornos GitHub `qa` y `github-pages`, configurar `QA_API_URL=https://api-talentsmart-qa.vexaperu.com`.

Los respaldos propios de Talent Smart se guardan en `/opt/talentsmart/backups`; no es una ruta de Nginx ni se publica por HTTP.

Asignar un dominio de API, por ejemplo `api-talentsmart-qa.vexaperu.com`, al VPS. Integrarlo en el proxy TLS existente usando `deploy/nginx/host.example.conf` como referencia, comprobar la configuración antes de recargar y usar un certificado válido.

El gateway de este proyecto publica **solo `127.0.0.1:9083`**; enruta `/voice/` a Talentosito y el resto a Django. No abre 80/443 ni administra los certificados del servidor. El proxy del host debe reenviar `Host` y establecer `X-Forwarded-Proto: https`. PostgreSQL, MinIO y su consola no publican puertos.

En `qa.env`:

- `DJANGO_ALLOWED_HOSTS`: dominio de API, `localhost,127.0.0.1,backend`.
- `CORS_ALLOWED_ORIGINS`: origen de Pages, por ejemplo `https://organizacion.github.io`, sin la ruta del repositorio.
- `CSRF_TRUSTED_ORIGINS`: dominio HTTPS de API para el admin de Django.
- `DJANGO_SETTINGS_MODULE=config.settings.qa`; no activar DEBUG.
- `GROQ_API_KEY`: necesaria únicamente para llamadas reales de voz.

El ESP32 utiliza directamente `https://DOMINIO_API_QA/api/rfid/registro` y `https://DOMINIO_API_QA/api/puerta/estado`, con la clave RFID de qa. El firmware se compila y carga físicamente; no se despliega mediante Compose ni Pages. Ver [guía del circuito](../iot/README.md).

Para la electrónica en qa, utilizar HTTPS y validar el certificado del servidor con las capacidades de la biblioteca ESP32. No desactivar la validación TLS. La compilación y prueba en el dispositivo físico se realizan por separado.

## Imágenes y GitHub Actions

El registro seleccionado es **GHCR**. Las imágenes de backend, Talentosito, MinIO y su cliente usan como etiqueta el SHA del commit desplegado. Configurar en el servidor un login de lectura a GHCR para esos paquetes, mediante una credencial de alcance limitado y `docker login ghcr.io --password-stdin`. No pasar la contraseña como argumento de línea de comandos.

MinIO comunitario se construye desde etiquetas fijadas del código oficial porque sus imágenes precompiladas no estuvieron disponibles durante la implementación. Su [repositorio oficial está archivado](https://github.com/minio/minio): la compilación propia resuelve la distribución, pero no proporciona mantenimiento upstream. Las versiones utilizadas están en `deploy/storage/Dockerfile`; revisar esta dependencia antes de ampliar qa a otros ambientes.

En el repositorio GitHub:

1. Habilitar Pages con origen **GitHub Actions**.
2. Crear el entorno **qa** y definir variables `QA_HOST`, `QA_USER`, `QA_SSH_PORT` y `QA_API_URL` (sin barra final).
3. Añadir a ese entorno los secretos `QA_SSH_KEY` y `QA_SSH_KNOWN_HOSTS`. Obtener la clave pública/huella del host mediante un canal confiable; no aceptar automáticamente una huella obtenida durante el despliegue.
4. En el entorno **github-pages**, definir también `QA_API_URL` y permitir la rama `qa`.
5. Dar al workflow permiso de escritura de paquetes y a Pages los permisos de despliegue.
6. Crear/promover la rama **qa**. Cada push ejecuta pruebas, construye las cuatro imágenes, despliega Hostinger y, solo si responde correctamente, publica Pages. La ejecución manual también requiere seleccionar `qa`.

`main` y `dev` ejecutan CI, pero no publican qa. El workflow anterior de Pages pasa a ser reutilizable y ya no compite con el despliegue coordinado. La compilación usa `frontend/package-lock.json` y publica `frontend/dist`.

El servidor debe tener memoria y disco suficientes para las imágenes, volúmenes y copias; la compilación pesada de MinIO ocurre en Actions, no en Hostinger.

## Primer despliegue y operación

Actions carga una entrega en `/opt/talentsmart/releases/COMMIT` y ejecuta `deploy/deploy-qa.sh`. El script verifica la configuración, descarga imágenes, prepara PostgreSQL/MinIO, pausa los servicios de escritura, respalda datos, migra y arranca. Una migración fallida detiene el despliegue y deja los servicios pausados para intervención; no intenta una reversión destructiva de datos.

Tras un despliegue correcto, abrir una sesión SSH y definir el helper:

```sh
cd /opt/talentsmart/current
dc() {
  docker compose --env-file /etc/talentsmart/qa.env --env-file release.env \
    -p talentsmart-qa -f compose.yaml -f compose.qa.yaml "$@"
}
dc exec backend python manage.py createsuperuser
dc ps
dc logs --tail 100 backend talentosito gateway
dc exec -T backend python manage.py smoke_test
```

El archivo `release.env` guarda solamente referencias de imágenes; los secretos permanecen en `/etc/talentsmart/qa.env`. La cuenta inicial del admin se crea interactivamente y no forma parte del pipeline ni del repositorio.

Verificar:

```sh
curl --fail https://DOMINIO_API_QA/api/health/ready/
curl --fail https://DOMINIO_API_QA/voice/
```

Después comprobar en Pages: login con una cuenta real, consulta del horario publicado, permisos de asistencia y descarga de reporte. Probar RFID y voz desde los dispositivos. El endpoint de salud de voz indica que el proceso responde; no garantiza que el proveedor Groq esté configurado o que el audio físico funcione.

Para detener únicamente esta aplicación conservando datos: `dc stop`. Para reiniciarla: `dc up -d --wait`. No ejecutar limpiezas globales de Docker ni `down --volumes` en qa.

## Respaldos y restauración

Cada despliegue crea `/opt/talentsmart/backups/FECHA-COMMIT/database.dump` y `files.tar` con permisos restringidos. El dump incluye metadatos, permisos y registros de Django; el tar contiene los objetos del bucket. Para una copia manual consistente, pausar gateway/backend/Talentosito, mantener PostgreSQL y MinIO activos y ejecutar en Bash:

```sh
umask 077
backup="/opt/talentsmart/backups/manual-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup"
dc stop gateway backend talentosito
dc exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$backup/database.dump"
dc run --rm -T --no-deps backend python manage.py backup_storage > "$backup/files.tar"
dc up -d --wait backend talentosito gateway
```

Copiar los respaldos a un destino externo protegido; su conservación y periodicidad fuera de despliegues deben configurarse según la operación del colegio. Conservar de manera separada y segura la configuración y claves necesarias para restaurar.

Para restaurar, elegir conscientemente un respaldo y una versión de aplicación compatibles, pausar los escritores y usar una base vacía de restauración o reemplazar deliberadamente la base de qa. El siguiente comando **reemplaza los objetos de la base objetivo**:

```sh
dc stop gateway backend talentosito
dc exec -T postgres sh -c 'pg_restore --exit-on-error --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < /RUTA/database.dump
dc run --rm -T --no-deps backend python manage.py restore_storage < /RUTA/files.tar
dc up -d --wait backend talentosito gateway
```

La restauración de archivos escribe objetos por nombre y no borra objetos sobrantes; estos no quedan accesibles sin metadatos/permisos de Django. Para una recuperación exacta, utilizar un bucket nuevo configurado e inicializado con su política antes de importar. Probar el respaldo en un conjunto aislado antes de sobrescribir qa.

## Reversión y fallos

Conservar la entrega anterior y su `release.env`. Si la migración es compatible, operar desde esa entrega con su archivo de imágenes y volver a levantar backend/Talentosito/gateway. Si no es compatible, restaurar primero el respaldo y usar la versión correspondiente; cambiar solo la imagen no revierte el esquema.

El frontend se publica después del backend: si Pages falla, el frontend anterior sigue activo. La API debe mantener compatibilidad durante esa ventana. Se puede volver a ejecutar el trabajo de Pages del despliegue compatible; no promover código antiguo con migraciones incompatibles sin revisar primero el estado de datos.

Errores habituales:

- 502 del proxy: revisar gateway y salud del backend; el script puede haber pausado servicios tras una migración fallida.
- 403 de CSRF solo en admin: revisar esquema HTTPS y dominio de confianza.
- API funciona con curl pero Pages falla: revisar el origen CORS y `QA_API_URL` del entorno github-pages.
- Descarga de imagen denegada: revisar login de GHCR y permisos de lectura del paquete del usuario del servidor.
- MinIO init falla: revisar las credenciales, disponibilidad y estado del volumen; no imprimir variables resueltas de Compose en logs.

