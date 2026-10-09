#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP_I2S.h>
#include <math.h>
#include "secrets.h"

// ESP32-C6-DevKitC-1
#define BUTTON_PIN 10

// INMP441: L/R conectado a GND (canal izquierdo).
#define MIC_BCLK 0
#define MIC_WS 1
#define MIC_SD 2

// MAX98357A
#define SPK_BCLK 3
#define SPK_LRC 4
#define SPK_DIN 5

#define MIC_SAMPLE_RATE 16000
#define RECORD_SECONDS 4
#define MIC_GAIN 8
#define MIN_SPEECH_RMS 400
#define SPEAKER_GAIN 2

// El ESP32-C6 usa un solo puerto I2S. Los dispositivos se activan por turnos.
I2SClass mic(I2S_NUM_0);
I2SClass speaker(I2S_NUM_0);
bool microphoneRunning = false;
bool speakerRunning = false;

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
  writeLE32(wav + 24, MIC_SAMPLE_RATE);
  writeLE32(wav + 28, MIC_SAMPLE_RATE * 2);
  writeLE16(wav + 32, 2);
  writeLE16(wav + 34, 16);
  memcpy(wav + 36, "data", 4);
  writeLE32(wav + 40, dataSize);
}

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

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

void stopMicrophone() {
  if (microphoneRunning) {
    mic.end();
    microphoneRunning = false;
    delay(10);
  }
}

void stopSpeaker() {
  if (speakerRunning) {
    speaker.end();
    speakerRunning = false;
    delay(10);
  }
}

bool startMicrophone() {
  stopSpeaker();
  mic.setPins(MIC_BCLK, MIC_WS, -1, MIC_SD);

  microphoneRunning = mic.begin(
    I2S_MODE_STD,
    MIC_SAMPLE_RATE,
    I2S_DATA_BIT_WIDTH_32BIT,
    I2S_SLOT_MODE_MONO,
    I2S_STD_SLOT_LEFT
  );

  Serial.println(
    microphoneRunning ? "INMP441 listo" : "ERROR iniciando INMP441"
  );
  return microphoneRunning;
}

bool startSpeaker(int sampleRate, int channels) {
  stopMicrophone();
  speaker.setPins(SPK_BCLK, SPK_LRC, SPK_DIN, -1);

  const i2s_slot_mode_t slotMode = channels == 2
    ? I2S_SLOT_MODE_STEREO
    : I2S_SLOT_MODE_MONO;

  speakerRunning = speaker.begin(
    I2S_MODE_STD,
    sampleRate,
    I2S_DATA_BIT_WIDTH_16BIT,
    slotMode
  );

  Serial.println(
    speakerRunning ? "MAX98357A listo" : "ERROR iniciando MAX98357A"
  );
  return speakerRunning;
}

void applySpeakerGain(uint8_t* buffer, size_t bytes) {
  if (SPEAKER_GAIN <= 1) {
    return;
  }

  for (size_t i = 0; i + 1 < bytes; i += 2) {
    const uint16_t rawSample = static_cast<uint16_t>(buffer[i])
      | (static_cast<uint16_t>(buffer[i + 1]) << 8);
    const int16_t sample = static_cast<int16_t>(rawSample);
    int32_t amplified = static_cast<int32_t>(sample) * SPEAKER_GAIN;
    amplified = constrain(amplified, -32768, 32767);

    const uint16_t clipped = static_cast<uint16_t>(
      static_cast<int16_t>(amplified)
    );
    buffer[i] = clipped & 0xFF;
    buffer[i + 1] = (clipped >> 8) & 0xFF;
  }
}

String getAssistantUrl() {
  String url = SERVER_URL;

  // Permite reutilizar un secrets.h creado durante las pruebas de STT.
  if (url.endsWith("/transcribe")) {
    url.remove(url.length() - String("/transcribe").length());
    url += "/ask";
  }

  return url;
}

uint8_t* recordAudio(size_t& wavSize, float& rms) {
  if (!microphoneRunning && !startMicrophone()) {
    return nullptr;
  }

  const uint32_t totalSamples = MIC_SAMPLE_RATE * RECORD_SECONDS;
  const uint32_t dataSize = totalSamples * sizeof(int16_t);
  wavSize = dataSize + 44;
  rms = 0;

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

  Serial.println("\n==============================");
  Serial.printf("HABLE AHORA (%d segundos)\n", RECORD_SECONDS);
  Serial.println("==============================");

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
      // Amplifica la muestra I2S completa antes de reducirla a 16 bits.
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

  rms = sqrt(static_cast<double>(squareSum) / totalSamples);
  const float clippedPercent = 100.0f * clippedSamples / totalSamples;

  Serial.printf(
    "WAV=%u bytes, offset=%ld, pico=%u, RMS=%.0f, saturado=%.2f%%\n",
    wavSize,
    dcOffset,
    peak,
    rms,
    clippedPercent
  );

  if (rms < MIN_SPEECH_RMS) {
    Serial.println("No se detecto voz suficiente; no se enviara el audio.");
  } else if (clippedPercent > 1.0f) {
    Serial.println("AVISO: audio saturado; reduzca MIC_GAIN.");
  }

  return wav;
}

bool playResponse(HTTPClient& http) {
  int sampleRate = http.header("X-Audio-Sample-Rate").toInt();
  int bits = http.header("X-Audio-Bits").toInt();
  int channels = http.header("X-Audio-Channels").toInt();

  if (sampleRate <= 0) sampleRate = 24000;
  if (bits <= 0) bits = 16;
  if (channels <= 0) channels = 1;

  Serial.printf(
    "Audio recibido: %d Hz, %d bits, %d canal(es), %d bytes\n",
    sampleRate,
    bits,
    channels,
    http.getSize()
  );

  if (bits != 16 || (channels != 1 && channels != 2)) {
    Serial.println("Formato PCM no compatible.");
    return false;
  }

  if (!startSpeaker(sampleRate, channels)) {
    return false;
  }

  NetworkClient* stream = http.getStreamPtr();
  if (!stream) {
    Serial.println("No se pudo obtener el stream HTTP.");
    stopSpeaker();
    return false;
  }

  int remaining = http.getSize();
  uint8_t buffer[2048];
  Serial.println("REPRODUCIENDO RESPUESTA...");

  while (http.connected() && (remaining > 0 || remaining == -1)) {
    size_t available = stream->available();
    if (available < 2) {
      delay(1);
      continue;
    }

    size_t bytesToRead = min(available, sizeof(buffer));
    bytesToRead &= ~static_cast<size_t>(1);
    const int bytesRead = stream->readBytes(buffer, bytesToRead);

    if (bytesRead > 0) {
      const size_t alignedBytes = bytesRead & ~static_cast<size_t>(1);
      if (alignedBytes > 0) {
        applySpeakerGain(buffer, alignedBytes);
        speaker.write(buffer, alignedBytes);
      }
      if (remaining > 0) {
        remaining -= bytesRead;
      }
    }
  }

  stopSpeaker();
  Serial.println("Reproduccion terminada.");
  return true;
}

void sendQuestion(uint8_t* wav, size_t wavSize) {
  connectWiFi();
  stopMicrophone();

  HTTPClient http;
  const String assistantUrl = getAssistantUrl();
  Serial.printf("Enviando %u bytes a %s\n", wavSize, assistantUrl.c_str());

  if (!http.begin(assistantUrl)) {
    Serial.println("No se pudo iniciar HTTP.");
    startMicrophone();
    return;
  }

  http.setTimeout(60000);
  const char* responseHeaders[] = {
    "X-Audio-Sample-Rate",
    "X-Audio-Bits",
    "X-Audio-Channels"
  };
  http.collectHeaders(responseHeaders, 3);
  http.addHeader("Content-Type", "audio/wav");
  http.addHeader("X-Device-Key", TALENTOSITO_DEVICE_KEY);
  http.addHeader("Accept", "application/octet-stream");

  const int status = http.POST(wav, wavSize);
  Serial.printf("HTTP status: %d\n", status);

  if (status == HTTP_CODE_OK) {
    playResponse(http);
  } else {
    const String response = http.getString();
    Serial.println("Error del servidor:");
    Serial.println(response.length() ? response : HTTPClient::errorToString(status));
  }

  http.end();

  if (!startMicrophone()) {
    Serial.println("No se pudo restaurar el microfono. Reiniciando...");
    delay(1000);
    ESP.restart();
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n==============================");
  Serial.println("ASISTENTE DE VOZ ESP32-C6");
  Serial.println("==============================");

  pinMode(BUTTON_PIN, INPUT_PULLUP);
  connectWiFi();

  if (!startMicrophone()) {
    Serial.println("Sistema detenido.");
    while (true) {
      delay(1000);
    }
  }

  Serial.println("Sistema listo. Pulse el boton para hablar.");
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
  float rms = 0;
  uint8_t* wav = recordAudio(wavSize, rms);

  if (wav) {
    if (rms >= MIN_SPEECH_RMS) {
      sendQuestion(wav, wavSize);
    }
    free(wav);
  }

  while (digitalRead(BUTTON_PIN) == LOW) {
    delay(10);
  }

  Serial.println("Pulse el boton para iniciar otro turno.");
  delay(300);
}
