# TalentSmart RFID Web

Web de presentación para el proyecto:

ESP32-C6 + RFID-RC522 + HC-SR04 + puerta automática + dashboard de rastreo.

## ¿Qué muestra?

- Dashboard de usuarios registrados.
- Accesos permitidos y denegados.
- Estado de puerta.
- Historial RFID.
- Formulario para registrar usuarios.
- Modo demo para simular lecturas RFID sin conectar todavía el ESP32.

## Requisitos

Instalar Node.js.

## Cómo ejecutar

1. Abre la carpeta del proyecto.
2. Ejecuta:

```bash
npm install
npm start
```

3. Abre en el navegador:

```text
http://localhost:3000
```

## Endpoint para el ESP32-C6

El ESP32 debe enviar un POST a:

```text
http://IP_DE_TU_PC:3000/api/rfid/registro
```

Ejemplo:

```json
{
  "uid": "A1B2C3D4",
  "device_id": "ESP32C6_RFID_01",
  "location_id": "PUERTA_PRINCIPAL",
  "event_type": "rfid_detected",
  "wifi_rssi": -54,
  "millis": 123456
}
```

Debe incluir el header:

```text
X-API-KEY: TALENT_SMART_KEY
```

## UIDs de prueba

La base inicial tiene estos UIDs autorizados:

```text
A1B2C3D4
11223344
55667788
```

Puedes registrar más usuarios desde la propia web.

## Para la exposición

Puedes explicar:

1. El usuario acerca su pulsera o tarjeta RFID.
2. El ESP32-C6 lee el UID.
3. La web valida si el UID pertenece a un usuario autorizado.
4. Si está autorizado, la puerta abre.
5. El HC-SR04 evita que la puerta cierre mientras una persona sigue pasando.
6. El dashboard registra quién entró, a qué hora y por qué punto de acceso.
