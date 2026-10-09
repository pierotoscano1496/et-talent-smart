# pagina-control — asistencia RFID

Subproyecto de robótica para la interacción de estudiantes con tarjetas, llaveros o pulseras RFID. Es distinto de [Talentosito](../talentosito/README.md), el asistente de consultas por voz. Ambos forman parte de Talent Smart y comparten las reglas y datos de Django.

## Componentes

- `esp32.cpp`: firmware ESP32-C6, lector RC522, sensor HC-SR04 y servo MG90S.
- `public/`: panel de administración de llaves y monitoreo RFID.
- `Dockerfile` y `nginx.conf`: panel estático y proxy de `/api/` hacia Django.
- Django guarda cuentas, llaves, lecturas, asistencia diaria y último estado de dispositivos en PostgreSQL. MinIO sigue reservado a archivos de la aplicación.
- `database.json` se conserva como archivo histórico de pruebas: ningún servicio lo lee o modifica. Las cuentas deben crearse en Django; no se importan registros históricos sin revisión.
- `server.js` ahora inicia el conjunto dev de Compose por compatibilidad con `npm start`. Ya no existe una API Express ni credencial de demostración.

## Arranque dev

Desde la raíz del repositorio:

```sh
node deploy/dev.mjs start
node deploy/dev.mjs admin
```

Panel: http://localhost:3000/. El administrador crea cuentas de estudiantes y asigna o retira llaves. El auxiliar consulta las lecturas recientes y la asistencia del día. Las cuentas de otros roles no acceden a este panel. Las sesiones se conservan solo en memoria y las claves del dispositivo nunca se entregan al navegador.

Grados, secciones y otras cuentas se gestionan mediante Django admin/API. El retiro temprano sigue siendo una incidencia registrada por el auxiliar, independiente del reporte de cierre de una puerta.

## Preparar el ESP32

1. Instalar Arduino IDE, plataforma Espressif ESP32 (3.x), bibliotecas MFRC522, ESP32Servo y ArduinoJson 7.
2. Crear un sketch Arduino vacío y agregar `esp32.cpp` como archivo fuente. Copiar `secrets.example.h` a `secrets.h` en la misma carpeta. Elegir ESP32-C6 Dev Module, o la placa exacta del dispositivo.
3. Completar Wi-Fi, identificadores únicos de dispositivo/ubicación y `API_KEY` con el valor privado `RFID_API_KEY` del ambiente. No usar la clave de Talentosito.
4. En dev, usar la IP LAN de la computadora y puerto 3000 para `SERVER_URL` y `SERVER_STATE_URL`. Configurar `DEV_BIND_IP=0.0.0.0` y añadir la IP a `DJANGO_ALLOWED_HOSTS` en `deploy/env/dev.env`; recrear backend y pagina-control. Permitir el puerto en el firewall local.
5. En qa, usar `https://DOMINIO_API_QA/rfid/api/rfid/registro` y `https://DOMINIO_API_QA/rfid/api/puerta/estado`. Establecer `ALLOW_INSECURE_HTTP=false`, pegar la CA raíz PEM válida en `TLS_ROOT_CA` y permitir sincronización NTP. No se desactiva la verificación del certificado.
6. Compilar, cargar y verificar las conexiones y ángulos en la maqueta antes de operar.

Pines conservados: RC522 SCK=6, MISO=2, MOSI=7, SS=10, RST=3; HC-SR04 TRIG=18, ECHO=19; servo=4. Verificar niveles eléctricos y alimentación correspondientes a la placa y sensores.

El firmware solo autoriza con HTTP 200 y JSON válido con `ok: true` y `authorized: true`. Ante una falla de red no autoriza: presentar nuevamente la tarjeta cuando se recupere. No hay cola persistente para asistencia sin conexión. Cada presentación usa un identificador de evento; el backend permite reintentar ese mismo evento sin duplicarlo y consolida todas las lecturas válidas del día en una asistencia.

Mientras la puerta está abierta, se prioriza el sensor y no se inician nuevas validaciones RFID. La telemetría usa una tarea aparte y comunica el último estado comandado al arrancar, al cambiar y cada 30 segundos; fallas de red no bloquean el control del sensor. Sin eco válido se mantiene abierta hasta obtener una medida válida de paso libre. Comprobar este comportamiento en el montaje físico.

El panel muestra el último reporte y su fecha. No hay sensor de posición ni confirmación de paso: la autorización o el reporte de estado no prueban que alguien haya cruzado. El panel no envía órdenes de apertura/cierre ni genera marcaciones simuladas.

## qa y pruebas

El workflow construye la imagen `pagina-control` con el SHA del commit. Compose la ejecuta en Hostinger detrás del gateway en `/rfid/`, sin publicar otro puerto del host. Las reglas y permisos se prueban con `node deploy/dev.mjs test`; la compilación de firmware y prueba física son verificaciones separadas.

Consultar [API](../docs/api.md), [dev](../docs/ejecucion-dev.md) y [qa](../docs/despliegue-qa.md). Referencias del firmware: [ArduinoJson 7](https://arduinojson.org/v7/api/json/deserializejson/) y [TLS ESP32](https://github.com/espressif/arduino-esp32/blob/master/libraries/NetworkClientSecure/README.md).
