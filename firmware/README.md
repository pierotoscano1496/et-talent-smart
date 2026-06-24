# Firmware ESP32

Firmware base para el `Nodo_Acceso` con ESP32 + RC522, alineado con los endpoints ya implementados del backend:

- `POST /access/events`
- `POST /access/heartbeat`
- `Authorization: Bearer <node_token>`

## Estado actual

Incluye:

- proyecto PlatformIO para `esp32dev`
- lectura RFID con `MFRC522`
- heartbeat periódico cada 60 s
- autenticación por token de nodo
- reintentos para respuestas HTTP no `2xx` y no `401`
- bloqueo local ante `401` hasta recibir nueva configuración
- activación de relay durante 3 segundos cuando `resultado=autorizado`
- consola Serial para configuración persistida en `Preferences` (NVS)

## Configuración por Serial

Abrir monitor serie a `115200` y usar:

```text
set wifi_ssid MiRed
set wifi_password MiClave
set backend_url https://192.168.1.10
set node_id NODO-LAB-01
set node_token <token-generado-en-management>
save
show
```

Comandos disponibles:

- `show`
- `save`
- `clear`
- `help`
- `set <clave> <valor>`

Claves soportadas:

- `wifi_ssid`
- `wifi_password`
- `backend_url`
- `node_id`
- `node_token`
- `timeout_ms`
- `max_retries`
- `retry_interval_ms`
- `heartbeat_interval_s`

## Flujo operativo

1. Carga configuración desde NVS.
2. Conecta a WiFi.
3. Envía un heartbeat inicial para validar token y marcar nodo en línea.
4. Lee tags RFID de 4 bytes y reporta `{tag_rfid, node_id, timestamp_utc}`.
5. Si recibe `resultado=autorizado`, activa el relay por `3000 ms`.
6. Si recibe `401`, entra en espera de nueva configuración.

## Notas

- El backend actual valida `node_id` también en el body de `POST /access/events`; por eso el firmware lo envía siempre.
- `POST /access/heartbeat` no requiere body específico en el backend actual; este firmware envía `{}`.
- En esta fase de desarrollo está habilitado `setInsecure()` para TLS (`kDevAllowInsecureTls = true`) por certificados locales. Para producción conviene reemplazarlo por validación de CA o pinning.
- El backend actual acepta `tag_rfid` de exactamente 8 caracteres hexadecimales, por lo que este firmware procesa solo UIDs de 4 bytes.
