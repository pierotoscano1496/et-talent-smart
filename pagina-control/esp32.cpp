#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <esp_system.h>
#include <time.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ESP32Servo.h>

// =====================================================
// CONFIGURACIÓN WIFI Y WEB
// =====================================================
#include "secrets.h"

// =====================================================
// PINES RFID RC522
// =====================================================
#define RFID_SCK   6
#define RFID_MISO  2
#define RFID_MOSI  7
#define RFID_SS    10
#define RFID_RST   3

MFRC522 rfid(RFID_SS, RFID_RST);

// =====================================================
// PINES HC-SR04
// =====================================================
#define ULTRASONIC_TRIG 18
#define ULTRASONIC_ECHO 19

// =====================================================
// SERVO MG90S
// =====================================================
#define SERVO_PIN 4

Servo doorServo;

// Ajusta estos ángulos según tu maqueta
const int SERVO_CLOSED_ANGLE = 0;
const int SERVO_OPEN_ANGLE = 90;

// Si tu puerta abre al lado contrario, cambia:
// cerrado = 90
// abierto = 0

// =====================================================
// CONFIGURACIÓN DE SEGURIDAD DE PUERTA
// =====================================================
const int PERSON_DETECT_CM = 70;
const unsigned long MIN_OPEN_TIME = 5000;
const unsigned long CLEAR_DELAY = 2500;
const unsigned long SONAR_INTERVAL = 150;

QueueHandle_t doorReports = nullptr;
String bootId;
unsigned long eventSequence = 0;
bool doorIsOpen = false;
unsigned long doorOpenedAt = 0;
unsigned long lastPresenceAt = 0;
unsigned long lastSonarRead = 0;

// =====================================================
// CONTROL DE LECTURAS RFID REPETIDAS
// =====================================================
String lastUID = "";
unsigned long lastReadTime = 0;
const unsigned long DUPLICATE_DELAY = 3000;

// =====================================================
// FUNCIÓN: UID A TEXTO
// =====================================================
String getUIDString(byte *buffer, byte bufferSize) {
  String uid = "";

  for (byte i = 0; i < bufferSize; i++) {
    if (buffer[i] < 0x10) {
      uid += "0";
    }

    uid += String(buffer[i], HEX);
  }

  uid.toUpperCase();
  return uid;
}

// =====================================================
// CONEXIÓN WIFI
// =====================================================
void connectWiFi() {
  Serial.println();
  Serial.println("Conectando a WiFi...");

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int intentos = 0;

  while (WiFi.status() != WL_CONNECTED && intentos < 30) {
    delay(500);
    Serial.print(".");
    intentos++;
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi conectado.");
    Serial.print("IP del ESP32-C6: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("No se pudo conectar al WiFi.");
  }
}

// =====================================================
// MEDIR DISTANCIA HC-SR04
// =====================================================
float getDistanceCM() {
  digitalWrite(ULTRASONIC_TRIG, LOW);
  delayMicroseconds(2);

  digitalWrite(ULTRASONIC_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(ULTRASONIC_TRIG, LOW);

  long duration = pulseIn(ULTRASONIC_ECHO, HIGH, 30000);

  if (duration == 0) {
    return -1;
  }

  float distance = duration * 0.0343 / 2.0;
  return distance;
}

// =====================================================
// ABRIR PUERTA CON SERVO
// =====================================================
void queueDoorState();

void openDoor() {
  if (!doorIsOpen) {
    Serial.println("Abriendo puerta con servo MG90S...");

    doorServo.write(SERVO_OPEN_ANGLE);
    delay(600);

    doorIsOpen = true;
    queueDoorState();
    doorOpenedAt = millis();
    lastPresenceAt = millis();

    Serial.println("Puerta abierta.");
  } else {
    Serial.println("La puerta ya está abierta.");
  }
}

// =====================================================
// AVISAR A LA WEB QUE LA PUERTA CERRÓ
// =====================================================
// Each call owns its clients; telemetry runs outside the sensor/servo loop.
int postJSON(const char* url, const String& payload, String& response) {
  if (WiFi.status() != WL_CONNECTED) return -1;
  WiFiClient plain;
  WiFiClientSecure secure;
  HTTPClient http;
  const String target(url);
  bool started = false;
  if (target.startsWith("https://")) {
    if (!TLS_ROOT_CA[0] || time(nullptr) < 1700000000) return -1;
    secure.setCACert(TLS_ROOT_CA);
    secure.setHandshakeTimeout(5);
    started = http.begin(secure, target);
  } else if (target.startsWith("http://") && ALLOW_INSECURE_HTTP) {
    started = http.begin(plain, target);
  }
  if (!started) return -1;
  http.setConnectTimeout(3000);
  http.setTimeout(3000);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-KEY", API_KEY);
  const int code = http.POST(payload);
  if (code == HTTP_CODE_OK) response = http.getString();
  http.end();
  return code;
}

void queueDoorState() {
  if (doorReports) xQueueOverwrite(doorReports, &doorIsOpen);
}

void reportDoorTask(void*) {
  bool state = false;
  // Send the latest commanded state at startup, on change, and every 30 seconds.
  for (;;) {
    xQueueReceive(doorReports, &state, pdMS_TO_TICKS(30000));
    JsonDocument body;
    body["device_id"] = DEVICE_ID;
    body["location_id"] = LOCATION_ID;
    body["state"] = state ? "abierta" : "cerrada";
    String payload, response;
    serializeJson(body, payload);
    const int code = postJSON(SERVER_STATE_URL, payload, response);
    Serial.printf("Estado de puerta HTTP: %d\n", code);
  }
}

// =====================================================
// CERRAR PUERTA CON SERVO
// =====================================================
void closeDoor() {
  if (doorIsOpen) {
    Serial.println("Cerrando puerta con servo MG90S...");

    doorServo.write(SERVO_CLOSED_ANGLE);
    delay(600);

    doorIsOpen = false;

    queueDoorState();

    Serial.println("Puerta cerrada.");
  }
}

// =====================================================
// ENVIAR UID A LA WEB Y VALIDAR AUTORIZACIÓN
// =====================================================
bool sendToWebAndCheckAuthorization(String uid) {
  // No offline authorizations; a failed request requires presenting the card again.
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.reconnect();
    return false;
  }
  JsonDocument body;
  body["uid"] = uid;
  body["device_id"] = DEVICE_ID;
  body["location_id"] = LOCATION_ID;
  body["event_id"] = bootId + "-" + String(++eventSequence);
  body["wifi_rssi"] = WiFi.RSSI();
  body["millis"] = millis();
  String payload, response;
  serializeJson(body, payload);
  const int code = postJSON(SERVER_URL, payload, response);
  Serial.printf("Lectura RFID HTTP: %d\n", code);
  if (code != HTTP_CODE_OK) return false;
  JsonDocument result;
  if (deserializeJson(result, response)) return false;
  return result["ok"].is<bool>() && result["ok"].as<bool>() &&
         result["authorized"].is<bool>() && result["authorized"].as<bool>();
}

// =====================================================
// SEGURIDAD DE PASO CON HC-SR04
// =====================================================
void updateDoorSafety() {
  if (!doorIsOpen) {
    return;
  }

  unsigned long now = millis();

  if (now - lastSonarRead < SONAR_INTERVAL) {
    return;
  }

  lastSonarRead = now;

  float distance = getDistanceCM();

  Serial.print("Distancia HC-SR04: ");
  Serial.print(distance);
  Serial.println(" cm");

  // A missing echo is not evidence that the path is clear.
  if (distance <= 0) {
    lastPresenceAt = now;
    return;
  }
  bool personDetected = false;

  if (distance > 0 && distance <= PERSON_DETECT_CM) {
    personDetected = true;
  }

  if (personDetected) {
    Serial.println("Persona detectada. La puerta sigue abierta.");
    lastPresenceAt = now;
    return;
  }

  bool minTimeCompleted = now - doorOpenedAt >= MIN_OPEN_TIME;
  bool pathClearForEnoughTime = now - lastPresenceAt >= CLEAR_DELAY;

  if (minTimeCompleted && pathClearForEnoughTime) {
    Serial.println("Paso libre. Cerrando puerta...");
    closeDoor();
  }
}

// =====================================================
// SETUP
// =====================================================
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("Sistema RFID + HC-SR04 + Servo MG90S iniciado.");

  pinMode(ULTRASONIC_TRIG, OUTPUT);
  pinMode(ULTRASONIC_ECHO, INPUT);

  // Servo MG90S
  doorServo.setPeriodHertz(50);
  doorServo.attach(SERVO_PIN, 500, 2500);
  doorServo.write(SERVO_CLOSED_ANGLE);

  connectWiFi();
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  bootId = String(esp_random(), HEX) + String(esp_random(), HEX);
  doorReports = xQueueCreate(1, sizeof(bool));
  if (doorReports) {
    queueDoorState();
    if (xTaskCreate(reportDoorTask, "door-reports", 8192, nullptr, 1, nullptr) != pdPASS) {
      vQueueDelete(doorReports);
      doorReports = nullptr;
      Serial.println("No se pudo iniciar la telemetria de puerta.");
    }
  }

  SPI.begin(RFID_SCK, RFID_MISO, RFID_MOSI, RFID_SS);
  rfid.PCD_Init();

  Serial.println("RC522 iniciado.");
  Serial.println("HC-SR04 iniciado.");
  Serial.println("Servo MG90S iniciado.");
  Serial.println("Acerca una tarjeta, llavero o pulsera RFID...");
}

// =====================================================
// LOOP PRINCIPAL
// =====================================================
void loop() {
  updateDoorSafety();
  // Avoid blocking HTTP or Wi-Fi reconnection while the passage is open.
  if (doorIsOpen) { delay(20); return; }

  if (!rfid.PICC_IsNewCardPresent()) {
    delay(20);
    return;
  }

  if (!rfid.PICC_ReadCardSerial()) {
    delay(20);
    return;
  }

  String uid = getUIDString(rfid.uid.uidByte, rfid.uid.size);

  Serial.println();
  Serial.println("Tarjeta detectada.");

  unsigned long now = millis();

  if (uid == lastUID && now - lastReadTime < DUPLICATE_DELAY) {
    Serial.println("Lectura repetida ignorada.");
  } else {
    bool authorized = sendToWebAndCheckAuthorization(uid);

    if (authorized) {
      Serial.println("Usuario autorizado. Abriendo puerta.");
      openDoor();
    } else {
      Serial.println("Usuario no autorizado. Puerta cerrada.");
    }

    lastUID = uid;
    lastReadTime = now;
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  delay(100);
}
