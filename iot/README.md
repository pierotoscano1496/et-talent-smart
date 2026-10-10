# iot — capa IoT RFID

Este directorio contiene el firmware del circuito RFID. El ESP32 envía las lecturas directamente a Django, que valida la llave y registra una asistencia por estudiante y día. La interfaz escolar está en `frontend/`; la administración de cuentas y llaves sigue disponible en Django admin/API. Talentosito es el otro subproyecto de robótica, dedicado a consultas por voz.

## Archivos

- `iot.ino`: sketch para abrir en Arduino IDE.
- `esp32.cpp`: implementación de lectura, red, autorización, sensor y servo.
- `pins.h`: perfiles de cableado ESP32 clásico y ESP32-C6.
- `secrets.example.h`: plantilla de Wi-Fi, API y certificado. Copiar a `secrets.h`, excluido de Git.

Esta capa se carga en el microcontrolador. No ejecuta un servidor web, base JSON ni contenedor. Docker Compose despliega las dependencias del servidor.

## Circuito

Seleccionar **ESP32 Dev Module** (WROOM-32) o **ESP32C6 Dev Module** según la placa física. Los números son GPIO, no posiciones del conector. El perfil C6 conserva el cableado anterior; el clásico utiliza otros GPIO para evitar los pines reservados a flash. [Referencia de Espressif](https://docs.espressif.com/projects/esp-faq/en/latest/hardware-related/hardware-design.html).

| Señal | ESP32 clásico | ESP32-C6 |
| --- | --- | --- |
| RC522 SCK | 18 | 6 |
| RC522 MISO | 19 | 2 |
| RC522 MOSI | 23 | 7 |
| RC522 SDA / SS (SPI) | 21 | 10 |
| RC522 RST | 22 | 3 |
| HC-SR04 TRIG | 26 | 18 |
| HC-SR04 ECHO | 27 | 19 |
| Servo MG90S señal | 25 | 4 |

RC522: alimentación a 3.3 V y tierra común. Servo: fuente de 5 V adecuada para su consumo, con tierra común; no alimentarlo desde un GPIO. HC-SR04 convencional: alimentación de 5 V y adaptación de ECHO a 3.3 V antes del ESP32, por ejemplo divisor de 1 kΩ desde ECHO al nodo GPIO y 2 kΩ del nodo a GND. Verificar las características de la variante física del sensor. No conectar señales de 5 V directamente a los GPIO del ESP32. Revisar también la disponibilidad de los pines en la placa concreta.

## Configuración y carga

1. Instalar la plataforma Arduino ESP32 3.x y las bibliotecas **ArduinoJson 7**, **MFRC522** y **ESP32Servo**. Las versiones usadas para la revisión son 7.4.3, 1.4.12 y 3.2.1 respectivamente.
2. Abrir `iot.ino`; Arduino compila también `esp32.cpp`. Copiar la plantilla a `secrets.h`.
3. Completar Wi-Fi, `DEVICE_ID` único, ubicación y `API_KEY` con `RFID_API_KEY` del mismo ambiente del backend.
4. Dev: configurar las URLs `http://IP_LAN_PC:8000/api/rfid/registro` y `http://IP_LAN_PC:8000/api/puerta/estado`. En el servidor usar `DEV_BIND_IP=0.0.0.0`, añadir la IP LAN a `DJANGO_ALLOWED_HOSTS` y permitir 8000 en el firewall local. Iniciar el servidor desde la raíz con `node deploy/dev.mjs start`.
5. Qa: usar `https://DOMINIO_API_QA/api/rfid/registro` y `https://DOMINIO_API_QA/api/puerta/estado`. Establecer `ALLOW_INSECURE_HTTP=false` y configurar `TLS_ROOT_CA` con la CA raíz PEM del servidor. HTTPS requiere hora sincronizada por NTP y certificado válido.
6. Elegir placa y puerto serie, compilar y cargar mediante Arduino IDE. Abrir el monitor a 115200 baudios. No cargar una compilación C6 en un ESP32 clásico.

Con Arduino CLI, desde la raíz y después de preparar `secrets.h`:

```sh
arduino-cli lib install "ArduinoJson@7.4.3" "MFRC522@1.4.12" "ESP32Servo@3.2.1"
arduino-cli compile --fqbn esp32:esp32:esp32 iot
# Para ESP32-C6:
arduino-cli compile --fqbn esp32:esp32:esp32c6 iot
# Cargar únicamente la variante de la placa conectada:
arduino-cli upload --fqbn esp32:esp32:esp32 --port PUERTO_SERIE iot
```

## Funcionamiento y prueba

Una lectura envía UID, dispositivo, ubicación y un identificador de evento. Los reintentos de red conservan el mismo evento (hasta tres intentos), para evitar duplicados. Solo HTTP 200 con JSON booleano `ok: true` y `authorized: true` permite accionar el servo. No hay autorización ni almacenamiento de asistencia offline.

El HC-SR04 mantiene el paso abierto mientras detecta presencia; ante ausencia de eco no asume paso libre. Mientras está abierto no inicia nuevas validaciones RFID. La telemetría se envía en una tarea independiente al arrancar, al cambiar de estado y cada 30 segundos; representa la última orden al servo, no una posición medida ni el paso efectivo del alumno. Los retiros tempranos se registran por el auxiliar en la aplicación escolar.

Verificar con una cuenta/llave creada por el administrador: tarjeta válida, desconocida, llave retirada, lecturas repetidas el mismo día, caída de Wi-Fi y presencia frente al sensor. Confirmar los resultados en Django. Ajustar ángulos y alimentación en la maqueta antes de conectar un mecanismo.

La compilación y la prueba física son comprobaciones separadas del backend. Consultar los resultados y versiones utilizados en [validación](../docs/validacion.md). No se ha cargado firmware ni probado el circuito físico durante esta adaptación.

Contrato: [API](../docs/api.md). Servidor: [dev](../docs/ejecucion-dev.md) y [qa](../docs/despliegue-qa.md). Bibliotecas: [SPI ESP32](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/spi.html) y [ESP32Servo](https://github.com/madhephaestus/ESP32Servo).
