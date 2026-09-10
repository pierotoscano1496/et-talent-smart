#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP_I2S.h>
#include <math.h>
#include "secrets.h"

// ESP32-C6-DevKitC-1 + INMP441
#define BUTTON_PIN 10
#define MIC_BCLK 0
#define MIC_WS 1
#define MIC_SD 2

#define SAMPLE_RATE 16000
#define RECORD_SECONDS 4
#define MIC_GAIN 8
#define MIN_SPEECH_RMS 400

I2SClass mic(I2S_NUM_0);

void writeLE16(uint8_t* buffer, uint16_t value) {
  buffer[0] = value & 0xFF;
  buffer[1] = (value >> 8) & 0xFF;
}

void writeLE32(uint8_t* buffer, uint32_t value) {
  buffer[0] = value & 0xFF;
  buffer[1] = (value >> 8) & 0xFF;
  buffer[2] = (value >> 16) & 0xFF;
  buffer[3] = (value >> 24) & 0xFF;
}

void createWavHeader(uint8_t* wav, uint32_t dataSize) {
  memcpy(wav + 0, "RIFF", 4);
  writeLE32(wav + 4, dataSize + 36);
  memcpy(wav + 8, "WAVE", 4);
  memcpy(wav + 12, "fmt ", 4);
  writeLE32(wav + 16, 16);
  writeLE16(wav + 20, 1);
  writeLE16(wav + 22, 1);
  writeLE32(wav + 24, SAMPLE_RATE);
  writeLE32(wav + 28, SAMPLE_RATE * 2);
  writeLE16(wav + 32, 2);
  writeLE16(wav + 34, 16);
  memcpy(wav + 36, "data", 4);
  writeLE32(wav + 40, dataSize);
}

void connectWiFi() {
  Serial.printf("Conectando a %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  for (int attempt = 0; WiFi.status() != WL_CONNECTED; attempt++) {
    if (attempt >= 40) {
      Serial.println("\nNo se pudo conectar. Reiniciando...");
      delay(1000);
      ESP.restart();
    }

    Serial.print(".");
    delay(500);
  }

  Serial.printf("\nWiFi conectado. IP: %s\n", WiFi.localIP().toString().c_str());
}

bool startMicrophone() {
  mic.setPins(MIC_BCLK, MIC_WS, -1, MIC_SD);

  return mic.begin(
    I2S_MODE_STD,
    SAMPLE_RATE,
    I2S_DATA_BIT_WIDTH_32BIT,
    I2S_SLOT_MODE_MONO,
    I2S_STD_SLOT_LEFT
  );
}

uint8_t* recordWav(size_t& wavSize) {
  const uint32_t totalSamples = SAMPLE_RATE * RECORD_SECONDS;
  const uint32_t dataSize = totalSamples * sizeof(int16_t);
  wavSize = dataSize + 44;

  uint8_t* wav = nullptr;
  if (psramFound()) {
    wav = static_cast<uint8_t*>(ps_malloc(wavSize));
  }
  if (!wav) {
    wav = static_cast<uint8_t*>(malloc(wavSize));
  }
  if (!wav) {
    Serial.printf("Sin memoria para %u bytes\n", wavSize);
    return nullptr;
  }

  createWavHeader(wav, dataSize);
  int16_t* pcm = reinterpret_cast<int16_t*>(wav + 44);
  int32_t raw[256];
  uint32_t captured = 0;
  int64_t sampleSum = 0;

  // Descarta el transitorio inicial del filtro interno del microfono.
  for (int block = 0; block < 12; block++) {
    mic.readBytes(reinterpret_cast<char*>(raw), sizeof(raw));
  }

  Serial.printf("\nHABLE AHORA (%d segundos)\n", RECORD_SECONDS);

  while (captured < totalSamples) {
    const uint32_t remaining = totalSamples - captured;
    const uint32_t requested = min(static_cast<uint32_t>(256), remaining);
    const size_t bytesRead = mic.readBytes(
      reinterpret_cast<char*>(raw),
      requested * sizeof(int32_t)
    );
    const uint32_t samplesRead = bytesRead / sizeof(int32_t);

    if (samplesRead == 0) {
      delay(1);
      continue;
    }

    for (uint32_t i = 0; i < samplesRead && captured < totalSamples; i++) {
      // Amplifica antes de reducir a 16 bits para conservar los bits utiles
      // de la salida I2S de 24 bits del INMP441.
      int32_t sample = static_cast<int32_t>(
        (static_cast<int64_t>(raw[i]) * MIC_GAIN) >> 16
      );
      sample = constrain(sample, -32768, 32767);
      pcm[captured++] = static_cast<int16_t>(sample);
      sampleSum += sample;
    }
  }

  const int32_t dcOffset = sampleSum / static_cast<int64_t>(totalSamples);
  uint32_t peak = 0;
  uint32_t clippedSamples = 0;
  uint64_t squareSum = 0;

  // Quita el offset DC antes de aplicar ganancia. El RMS resultante mide
  // sonido real y no un desplazamiento electrico constante.
  for (uint32_t i = 0; i < totalSamples; i++) {
    int32_t sample = static_cast<int32_t>(pcm[i]) - dcOffset;

    if (sample > 32767) {
      sample = 32767;
      clippedSamples++;
    } else if (sample < -32768) {
      sample = -32768;
      clippedSamples++;
    }

    pcm[i] = static_cast<int16_t>(sample);
    const uint32_t magnitude = abs(sample);
    peak = max(peak, magnitude);
    squareSum += static_cast<int64_t>(sample) * sample;
  }

  const float rms = sqrt(static_cast<double>(squareSum) / totalSamples);
  const float clippedPercent = 100.0f * clippedSamples / totalSamples;
  Serial.printf(
    "Grabacion lista: %u bytes, offset=%ld, pico=%u, RMS=%.0f, saturado=%.2f%%\n",
    wavSize,
    dcOffset,
    peak,
    rms,
    clippedPercent
  );

  if (rms < MIN_SPEECH_RMS) {
    Serial.println("ERROR: no se detecto voz con nivel suficiente.");
    Serial.println("No se enviara el audio para evitar una transcripcion inventada.");
  } else if (clippedPercent > 1.0f) {
    Serial.println("AVISO: audio saturado; reduzca MIC_GAIN.");
  }

  return wav;
}

void requestTranscription(uint8_t* wav, size_t wavSize) {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  HTTPClient http;
  Serial.printf("Enviando %u bytes a %s\n", wavSize, STT_SERVER_URL);

  if (!http.begin(STT_SERVER_URL)) {
    Serial.println("No se pudo iniciar la conexion HTTP.");
    return;
  }

  http.setTimeout(60000);

  const char* responseHeaders[] = {
    "X-Input-RMS",
    "X-Input-Peak",
    "X-STT-No-Speech-Probability",
    "X-STT-Avg-Logprob"
  };
  http.collectHeaders(responseHeaders, 4);

  http.addHeader("Content-Type", "audio/wav");
  http.addHeader("Accept", "text/plain");

  const int status = http.POST(wav, wavSize);
  const String response = http.getString();

  Serial.printf("HTTP status: %d\n", status);

  if (status == HTTP_CODE_OK) {
    Serial.printf(
      "Servidor: RMS=%s, pico=%s, no_speech=%s, avg_logprob=%s\n",
      http.header("X-Input-RMS").c_str(),
      http.header("X-Input-Peak").c_str(),
      http.header("X-STT-No-Speech-Probability").c_str(),
      http.header("X-STT-Avg-Logprob").c_str()
    );
    Serial.println("\n==============================");
    Serial.println("TEXTO RECONOCIDO");
    Serial.println("==============================");
    Serial.println(response);
    Serial.println("==============================\n");
  } else {
    Serial.println("Error de transcripcion:");
    Serial.println(response.length() ? response : HTTPClient::errorToString(status));
  }

  http.end();
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(BUTTON_PIN, INPUT_PULLUP);
  connectWiFi();

  if (!startMicrophone()) {
    Serial.println("No se pudo iniciar el INMP441.");
    while (true) {
      delay(1000);
    }
  }

  Serial.println("\nPrueba STT lista. Pulse el boton para grabar.");
}

void loop() {
  if (digitalRead(BUTTON_PIN) != LOW) {
    delay(10);
    return;
  }

  delay(50);
  if (digitalRead(BUTTON_PIN) != LOW) {
    return;
  }

  size_t wavSize = 0;
  uint8_t* wav = recordWav(wavSize);

  if (wav) {
    const int16_t* pcm = reinterpret_cast<const int16_t*>(wav + 44);
    const uint32_t totalSamples = SAMPLE_RATE * RECORD_SECONDS;
    uint64_t squareSum = 0;

    for (uint32_t i = 0; i < totalSamples; i++) {
      squareSum += static_cast<int64_t>(pcm[i]) * pcm[i];
    }

    const float rms = sqrt(static_cast<double>(squareSum) / totalSamples);
    if (rms >= MIN_SPEECH_RMS) {
      requestTranscription(wav, wavSize);
    }

    free(wav);
  }

  while (digitalRead(BUTTON_PIN) == LOW) {
    delay(10);
  }

  Serial.println("Pulse el boton para repetir la prueba.");
  delay(300);
}
