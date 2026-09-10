# Proyecto IA APIs - Asistente de voz con ESP32-C6

Backend FastAPI para recibir audio WAV desde un ESP32-C6, procesarlo con Groq y devolver audio PCM para reproducirlo en el dispositivo.

## Estructura

- `server.py`: API FastAPI.
- `codigo.ino`: firmware principal para el flujo STT, chat y TTS.
- `esp32_stt_test/`: firmware aislado para comprobar la transcripcion.
- `secrets.example.h`: plantilla de configuracion Wi-Fi y URL del backend.
- `.env.example`: plantilla de variables de entorno del backend.
- `tests/`: pruebas automatizadas de la API.
- `requirements.txt`: dependencias Python.

## Archivos locales no versionados

Estos archivos contienen secretos o estado local y quedan ignorados por Git:

- `.env`
- `secrets.h`
- `.venv/`
- `__pycache__/`

## Backend

Crear y activar el entorno virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Crear `.env` desde la plantilla:

```powershell
Copy-Item .env.example .env
```

Editar `.env`:

```env
GROQ_API_KEY=tu_api_key_aqui
GROQ_MAX_RETRIES=4
GROQ_TIMEOUT_SECONDS=60
GROQ_STT_MODEL=whisper-large-v3-turbo
GROQ_STT_MIN_RMS=80
GROQ_STT_MAX_NO_SPEECH_PROBABILITY=0.6
GROQ_CHAT_MODEL=openai/gpt-oss-120b
GROQ_CHAT_TEMPERATURE=0.7
GROQ_CHAT_MAX_COMPLETION_TOKENS=96
GROQ_CHAT_TOP_P=1
GROQ_TTS_MODEL=canopylabs/orpheus-v1-english
GROQ_TTS_VOICE=troy
GROQ_TTS_MAX_CHARS=190
```

Nota: el TTS Orpheus de Groq documentado actualmente ofrece modelos para ingles y arabe, y limita el `input` a 200 caracteres. El backend mantiene respuestas en espanol, pide respuestas breves y recorta el texto de TTS con `GROQ_TTS_MAX_CHARS` para evitar errores `BadRequest`.

Antes de usar TTS por primera vez, un admin de la organizacion debe aceptar los terminos del modelo en Groq Console:

```text
https://console.groq.com/playground?model=canopylabs%2Forpheus-v1-english
```

Ejecutar la API:

```powershell
uvicorn server:app --host 0.0.0.0 --port 8000
```

La API quedara disponible en:

```text
http://localhost:8000
```

## Contrato de la API

`GET /`

Devuelve un JSON de estado del servidor.

`POST /ask`

Recibe un cuerpo WAV y devuelve PCM crudo con estos headers:

- `X-Audio-Sample-Rate`
- `X-Audio-Bits`
- `X-Audio-Channels`

Si no se envia audio, responde `400`.

`POST /transcribe`

Recibe el mismo cuerpo WAV y devuelve solamente el texto reconocido como
`text/plain; charset=utf-8`. Este endpoint no ejecuta chat ni TTS.
Antes de llamar a Groq, rechaza WAV silenciosos mediante su RMS. Tambien usa
los metadatos `no_speech_prob` de Whisper para descartar transcripciones
inventadas sobre silencio o ruido.

Si Groq rechaza una solicitud, responde `502` con la etapa que fallo:

```json
{
  "detail": {
    "provider": "groq",
    "stage": "tts",
    "error": "BadRequestError",
    "message": "mensaje devuelto por Groq",
    "action": "accion correctiva si el error es conocido"
  }
}
```

## Pruebas

Ejecutar:

```powershell
python -m unittest discover -s tests -v
```

Para probar Groq real por etapas con la clave local de `.env`:

```powershell
python tools\diagnose_groq.py
```

Para probar solo chat y TTS:

```powershell
python tools\diagnose_groq.py --skip-stt
```

Las pruebas actuales validan:

- Estado de `GET /`.
- Flujo exitoso de `POST /ask` sin llamar a Groq real.
- Recorte de texto antes del TTS de Groq.
- Reporte de etapa cuando Groq devuelve error.
- Rechazo de `POST /ask` con cuerpo vacio.
- Headers de audio que consume el ESP32-C6.
- Transcripcion aislada sin invocar chat ni TTS.

## ESP32-C6

Crear `secrets.h` desde la plantilla:

```powershell
Copy-Item secrets.example.h secrets.h
```

Editar `secrets.h`:

```cpp
const char* WIFI_SSID = "NOMBRE_DE_TU_WIFI";
const char* WIFI_PASSWORD = "PASSWORD_DE_TU_WIFI";
const char* SERVER_URL = "http://192.168.1.100:8000/ask";
```

`SERVER_URL` debe apuntar a la IP de la computadora donde corre FastAPI. El ESP32-C6 y la computadora deben estar en la misma red.

### Pines actuales

Boton:

- `BUTTON_PIN` -> GPIO 10

Microfono INMP441:

- `BCLK` -> GPIO 0
- `WS` -> GPIO 1
- `SD` -> GPIO 2

Amplificador MAX98357A:

- `BCLK` -> GPIO 3
- `LRC` -> GPIO 4
- `DIN` -> GPIO 5

### Prueba aislada de Speech-to-Text

El sketch `esp32_stt_test/esp32_stt_test.ino` solo usa el boton y el INMP441.
Graba cuatro segundos, envia el WAV a `POST /transcribe` y muestra el texto en
el monitor serial a 115200 baudios. No consulta el modelo de chat ni genera voz.

Preparar su configuracion local:

```powershell
Copy-Item esp32_stt_test\secrets.example.h esp32_stt_test\secrets.h
```

En `esp32_stt_test/secrets.h`, configurar `STT_SERVER_URL` con la IP real del
servidor y la ruta `/transcribe`, por ejemplo:

```cpp
const char* STT_SERVER_URL = "http://192.168.88.86:8000/transcribe";
```

Abrir `esp32_stt_test/esp32_stt_test.ino` en Arduino IDE, cargarlo al ESP32-C6
y pulsar el boton. El monitor serial mostrara el nivel del audio y la frase
reconocida.

Si el RMS es menor que `400`, el firmware no envia el WAV. Esto evita frases
como `Gracias` generadas por Whisper cuando el microfono entrega silencio. La
conversion aplica `MIC_GAIN` antes de reducir las muestras I2S a 16 bits y
elimina el offset DC. El monitor serial tambien muestra `no_speech_prob` y
`avg_logprob` devueltos por Groq para evaluar la calidad de la transcripcion.

## Flujo de trabajo recomendado

1. Ejecutar pruebas del backend.
2. Levantar FastAPI en `0.0.0.0:8000`.
3. Verificar `GET http://localhost:8000/`.
4. Configurar `secrets.h` con la IP local correcta.
5. Compilar y subir `codigo.ino` al ESP32-C6.
6. Probar una grabacion corta y revisar logs del monitor serial y del backend.

El firmware principal conmuta el unico puerto I2S del ESP32-C6: primero activa
el INMP441 para grabar, libera el puerto antes de la consulta y despues activa
el MAX98357A para reproducir la respuesta. Al terminar restaura el microfono
para el siguiente turno.

Si `SERVER_URL` aun termina en `/transcribe`, el firmware principal cambia esa
ruta a `/ask` automaticamente. Para evitar ambiguedades, se recomienda dejar
la configuracion explicita:

```cpp
const char* SERVER_URL = "http://192.168.88.76:8000/ask";
```
