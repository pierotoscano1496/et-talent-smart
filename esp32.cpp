#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ESP32Servo.h>

// =====================================================
// CONFIGURACIÓN WIFI Y WEB
// =====================================================
const char* WIFI_SSID = "AP-ROBOTICA";
const char* WIFI_PASSWORD = "Piero-456";

const char* SERVER_URL = "https://tifany-coxal-unpresidentially.ngrok-free.dev/api/rfid/registro";
const char* SERVER_CLOSE_URL = "https://tifany-coxal-unpresidentially.ngrok-free.dev/api/puerta/cerrar";

const char* API_KEY = "TALENT_SMART_KEY";

const char* DEVICE_ID = "ESP32C6_RFID_01";
const char* LOCATION_ID = "PUERTA_PRINCIPAL";

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
void openDoor() {
  if (!doorIsOpen) {
    Serial.println("Abriendo puerta con servo MG90S...");

    doorServo.write(SERVO_OPEN_ANGLE);
    delay(600);

    doorIsOpen = true;
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
void notifyDoorClosedToWeb() {
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  HTTPClient http;
  http.begin(SERVER_CLOSE_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-KEY", API_KEY);

  int httpCode = http.POST("{}");

  Serial.print("Aviso cierre puerta HTTP: ");
  Serial.println(httpCode);

  http.end();
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

    notifyDoorClosedToWeb();

    Serial.println("Puerta cerrada.");
  }
}

// =====================================================
// ENVIAR UID A LA WEB Y VALIDAR AUTORIZACIÓN
// =====================================================
bool sendToWebAndCheckAuthorization(String uid) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi desconectado. Reintentando...");
    connectWiFi();

    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("No hay WiFi. Acceso denegado.");
      return false;
    }
  }

  HTTPClient http;

  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-KEY", API_KEY);

  String payload = "{";
  payload += "\"uid\":\"" + uid + "\",";
  payload += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  payload += "\"location_id\":\"" + String(LOCATION_ID) + "\",";
  payload += "\"event_type\":\"rfid_detected\",";
  payload += "\"wifi_rssi\":" + String(WiFi.RSSI()) + ",";
  payload += "\"millis\":" + String(millis());
  payload += "}";

  Serial.println("Enviando a la web:");
  Serial.println(payload);

  int httpCode = http.POST(payload);

  Serial.print("Código HTTP: ");
  Serial.println(httpCode);

  bool authorized = false;

  if (httpCode > 0) {
    String response = http.getString();

    Serial.println("Respuesta del servidor:");
    Serial.println(response);

    response.replace(" ", "");
    response.replace("\n", "");
    response.replace("\r", "");

    if (response.indexOf("\"authorized\":true") >= 0) {
      authorized = true;
    }
  } else {
    Serial.println("Error enviando datos a la web.");
  }

  http.end();

  return authorized;
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
  Serial.print("UID detectado: ");
  Serial.println(uid);

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