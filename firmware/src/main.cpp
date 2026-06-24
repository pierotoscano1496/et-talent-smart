#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <MFRC522.h>
#include <Preferences.h>
#include <SPI.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <time.h>

#include "config.h"
#include "pins.h"
#include "state_machine.h"

namespace {

constexpr size_t kLocalLogCapacity = 16;
constexpr unsigned long kWifiConnectTimeoutMs = 20000;
constexpr unsigned long kStatusPulseMs = 250;
constexpr unsigned long kAccessOpenDurationMs = 3000;

struct LocalLogEntry {
  String timestamp;
  String status;
  String detail;
};

struct ApiResult {
  bool success = false;
  bool timed_out = false;
  bool auth_error = false;
  int http_code = 0;
  String result;
  String code;
  String event_id;
};

Preferences preferences;
WiFiClientSecure secure_client;
MFRC522 mfrc522(Pins::kRfidSda, Pins::kRfidRst);
NodeConfig node_config = defaultNodeConfig();

FirmwareState current_state = FirmwareState::Inicializando;
bool node_authenticated = false;
bool auth_locked = false;
bool relay_active = false;
bool deny_feedback_active = false;
unsigned long relay_started_ms = 0;
unsigned long deny_feedback_started_ms = 0;
unsigned long last_heartbeat_attempt_ms = 0;
unsigned long last_status_print_ms = 0;
LocalLogEntry local_logs[kLocalLogCapacity];
size_t local_log_index = 0;

String serial_buffer;

void setState(FirmwareState next_state) {
  if (current_state == next_state) {
    return;
  }
  current_state = next_state;
  Serial.printf("[STATE] %s\n", stateName(current_state));
}

void appendLocalLog(const String& status, const String& detail) {
  LocalLogEntry& slot = local_logs[local_log_index % kLocalLogCapacity];
  slot.timestamp = String(millis());
  slot.status = status;
  slot.detail = detail;
  local_log_index++;
  Serial.printf("[LOCAL] %s | %s | %s\n", slot.timestamp.c_str(), status.c_str(),
                detail.c_str());
}

String trimTrailingSlash(const String& value) {
  String normalized = value;
  while (normalized.endsWith("/")) {
    normalized.remove(normalized.length() - 1);
  }
  return normalized;
}

bool configLooksValid() {
  return strlen(node_config.wifi_ssid) > 0 && strlen(node_config.backend_url) > 0 &&
         strlen(node_config.node_id) > 0 && strlen(node_config.node_token) > 0;
}

void readPreferencesConfig() {
  node_config = defaultNodeConfig();
  preferences.begin(kPreferencesNamespace, true);
  preferences.getString("wifi_ssid", node_config.wifi_ssid, sizeof(node_config.wifi_ssid));
  preferences.getString("wifi_pass", node_config.wifi_password,
                        sizeof(node_config.wifi_password));
  preferences.getString("backend_url", node_config.backend_url,
                        sizeof(node_config.backend_url));
  preferences.getString("node_id", node_config.node_id, sizeof(node_config.node_id));
  preferences.getString("node_token", node_config.node_token,
                        sizeof(node_config.node_token));
  node_config.timeout_ms = preferences.getUShort("timeout_ms", node_config.timeout_ms);
  node_config.max_retries = preferences.getUChar("max_retries", node_config.max_retries);
  node_config.retry_interval_ms =
      preferences.getUShort("retry_ms", node_config.retry_interval_ms);
  node_config.heartbeat_interval_s =
      preferences.getUShort("heartbeat_s", node_config.heartbeat_interval_s);
  preferences.end();
}

void writePreferencesConfig() {
  preferences.begin(kPreferencesNamespace, false);
  preferences.putString("wifi_ssid", node_config.wifi_ssid);
  preferences.putString("wifi_pass", node_config.wifi_password);
  preferences.putString("backend_url", node_config.backend_url);
  preferences.putString("node_id", node_config.node_id);
  preferences.putString("node_token", node_config.node_token);
  preferences.putUShort("timeout_ms", node_config.timeout_ms);
  preferences.putUChar("max_retries", node_config.max_retries);
  preferences.putUShort("retry_ms", node_config.retry_interval_ms);
  preferences.putUShort("heartbeat_s", node_config.heartbeat_interval_s);
  preferences.end();
}

void clearPreferencesConfig() {
  preferences.begin(kPreferencesNamespace, false);
  preferences.clear();
  preferences.end();
}

void printConfig() {
  Serial.println("Configuracion actual:");
  Serial.printf("  wifi_ssid=%s\n", node_config.wifi_ssid);
  Serial.printf("  wifi_password=%s\n",
                strlen(node_config.wifi_password) > 0 ? "<configurado>" : "<vacio>");
  Serial.printf("  backend_url=%s\n", node_config.backend_url);
  Serial.printf("  node_id=%s\n", node_config.node_id);
  Serial.printf("  node_token=%s\n",
                strlen(node_config.node_token) > 0 ? "<configurado>" : "<vacio>");
  Serial.printf("  timeout_ms=%u\n", node_config.timeout_ms);
  Serial.printf("  max_retries=%u\n", node_config.max_retries);
  Serial.printf("  retry_interval_ms=%u\n", node_config.retry_interval_ms);
  Serial.printf("  heartbeat_interval_s=%u\n", node_config.heartbeat_interval_s);
  Serial.printf("  estado=%s\n", stateName(current_state));
}

void printHelp() {
  Serial.println("Comandos serial disponibles:");
  Serial.println("  show");
  Serial.println("  save");
  Serial.println("  clear");
  Serial.println("  help");
  Serial.println("  set wifi_ssid <valor>");
  Serial.println("  set wifi_password <valor>");
  Serial.println("  set backend_url <valor>");
  Serial.println("  set node_id <valor>");
  Serial.println("  set node_token <valor>");
  Serial.println("  set timeout_ms <valor>");
  Serial.println("  set max_retries <valor>");
  Serial.println("  set retry_interval_ms <valor>");
  Serial.println("  set heartbeat_interval_s <valor>");
}

void copyStringValue(const String& source, char* target, size_t size) {
  source.substring(0, size - 1).toCharArray(target, size);
}

bool applySerialSetting(const String& key, const String& value) {
  if (key == "wifi_ssid") {
    copyStringValue(value, node_config.wifi_ssid, sizeof(node_config.wifi_ssid));
    return true;
  }
  if (key == "wifi_password") {
    copyStringValue(value, node_config.wifi_password, sizeof(node_config.wifi_password));
    return true;
  }
  if (key == "backend_url") {
    String normalized = trimTrailingSlash(value);
    copyStringValue(normalized, node_config.backend_url, sizeof(node_config.backend_url));
    return true;
  }
  if (key == "node_id") {
    copyStringValue(value, node_config.node_id, sizeof(node_config.node_id));
    return true;
  }
  if (key == "node_token") {
    copyStringValue(value, node_config.node_token, sizeof(node_config.node_token));
    return true;
  }
  if (key == "timeout_ms") {
    node_config.timeout_ms = static_cast<uint16_t>(value.toInt());
    return true;
  }
  if (key == "max_retries") {
    node_config.max_retries = static_cast<uint8_t>(value.toInt());
    return true;
  }
  if (key == "retry_interval_ms") {
    node_config.retry_interval_ms = static_cast<uint16_t>(value.toInt());
    return true;
  }
  if (key == "heartbeat_interval_s") {
    node_config.heartbeat_interval_s = static_cast<uint16_t>(value.toInt());
    return true;
  }
  return false;
}

void processSerialCommand(const String& raw_command) {
  String command = raw_command;
  command.trim();
  if (command.isEmpty()) {
    return;
  }

  if (command == "show") {
    printConfig();
    return;
  }
  if (command == "help") {
    printHelp();
    return;
  }
  if (command == "save") {
    writePreferencesConfig();
    auth_locked = false;
    node_authenticated = false;
    last_heartbeat_attempt_ms = 0;
    appendLocalLog("config-guardada", "Configuracion persistida en NVS");
    return;
  }
  if (command == "clear") {
    clearPreferencesConfig();
    node_config = defaultNodeConfig();
    auth_locked = false;
    node_authenticated = false;
    last_heartbeat_attempt_ms = 0;
    appendLocalLog("config-limpiada", "Configuracion eliminada de NVS");
    return;
  }

  if (!command.startsWith("set ")) {
    Serial.println("Comando no reconocido. Usa 'help'.");
    return;
  }

  int key_start = 4;
  int separator = command.indexOf(' ', key_start);
  if (separator < 0) {
    Serial.println("Formato esperado: set <clave> <valor>");
    return;
  }

  String key = command.substring(key_start, separator);
  String value = command.substring(separator + 1);
  value.trim();
  if (value.isEmpty()) {
    Serial.println("Valor vacio no permitido.");
    return;
  }

  if (!applySerialSetting(key, value)) {
    Serial.println("Clave no soportada. Usa 'help'.");
    return;
  }

  Serial.printf("Actualizado: %s\n", key.c_str());
}

void pollSerialConsole() {
  while (Serial.available() > 0) {
    char current = static_cast<char>(Serial.read());
    if (current == '\r') {
      continue;
    }
    if (current == '\n') {
      processSerialCommand(serial_buffer);
      serial_buffer = "";
      continue;
    }
    serial_buffer += current;
  }
}

void configurePins() {
  pinMode(Pins::kRelay, OUTPUT);
  pinMode(Pins::kLedGranted, OUTPUT);
  pinMode(Pins::kLedDenied, OUTPUT);
  pinMode(Pins::kBuzzer, OUTPUT);

  digitalWrite(Pins::kRelay, LOW);
  digitalWrite(Pins::kLedGranted, LOW);
  digitalWrite(Pins::kLedDenied, LOW);
  digitalWrite(Pins::kBuzzer, LOW);
}

void syncClock() {
  configTime(0, 0, "pool.ntp.org", "time.nist.gov", "time.google.com");
  for (uint8_t attempt = 0; attempt < 20; ++attempt) {
    time_t now = time(nullptr);
    if (now > 1704067200) {
      Serial.println("[TIME] Reloj NTP sincronizado");
      return;
    }
    delay(250);
  }
  Serial.println("[TIME] No se logro sincronizar NTP al inicio");
}

String currentTimestampUtc() {
  time_t now = time(nullptr);
  struct tm timeinfo {};
  gmtime_r(&now, &timeinfo);
  char buffer[32];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
  return String(buffer);
}

bool ensureWiFiConnected() {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }

  setState(FirmwareState::Conectando_WiFi);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(node_config.wifi_ssid, node_config.wifi_password);

  unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < kWifiConnectTimeoutMs) {
    pollSerialConsole();
    delay(250);
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[WIFI] Conectado. IP=%s\n", WiFi.localIP().toString().c_str());
    syncClock();
    return true;
  }

  appendLocalLog("wifi-desconectado", "No fue posible conectar a la red WiFi");
  return false;
}

String endpointUrl(const char* path) {
  String base = trimTrailingSlash(String(node_config.backend_url));
  return base + path;
}

void prepareSecureClient() {
  if (kDevAllowInsecureTls) {
    secure_client.setInsecure();
  }
}

ApiResult postJsonWithAuth(const char* path, const String& payload_json, bool include_body) {
  ApiResult result;
  if (!ensureWiFiConnected()) {
    result.http_code = -1;
    return result;
  }

  prepareSecureClient();
  HTTPClient http;
  if (!http.begin(secure_client, endpointUrl(path))) {
    result.http_code = -2;
    return result;
  }

  http.setConnectTimeout(node_config.timeout_ms);
  http.setTimeout(node_config.timeout_ms);
  http.addHeader("Authorization", String("Bearer ") + node_config.node_token);
  http.addHeader("Content-Type", "application/json");

  int http_code = include_body ? http.POST(payload_json) : http.POST("{}");
  result.http_code = http_code;

  if (http_code == HTTPC_ERROR_CONNECTION_REFUSED || http_code == HTTPC_ERROR_READ_TIMEOUT ||
      http_code == HTTPC_ERROR_CONNECTION_LOST) {
    result.timed_out = (http_code == HTTPC_ERROR_READ_TIMEOUT);
    http.end();
    return result;
  }

  if (http_code == 401) {
    result.auth_error = true;
  }

  if (http_code > 0) {
    String body = http.getString();
    StaticJsonDocument<512> document;
    if (deserializeJson(document, body) == DeserializationError::Ok) {
      result.result = document["resultado"] | "";
      result.code = document["codigo_resultado"] | "";
      result.event_id = document["evento_id"] | "";
    }
    result.success = http_code >= 200 && http_code < 300;
  }

  http.end();
  return result;
}

bool sendHeartbeat() {
  setState(FirmwareState::Enviando_Heartbeat);
  last_heartbeat_attempt_ms = millis();
  ApiResult response = postJsonWithAuth("/access/heartbeat", "{}", false);

  if (response.auth_error) {
    auth_locked = true;
    node_authenticated = false;
    setState(FirmwareState::Error_Auth);
    appendLocalLog("error-autenticacion", "HTTP 401 en heartbeat");
    return false;
  }

  if (response.success) {
    node_authenticated = true;
    appendLocalLog("heartbeat-ok", "Heartbeat recibido por backend");
    return true;
  }

  if (response.timed_out) {
    appendLocalLog("heartbeat-timeout", "Timeout al enviar heartbeat");
  } else {
    appendLocalLog("heartbeat-error", "HTTP " + String(response.http_code));
  }
  return false;
}

void activateAccessSignal() {
  digitalWrite(Pins::kRelay, HIGH);
  digitalWrite(Pins::kLedGranted, HIGH);
  relay_active = true;
  relay_started_ms = millis();
}

void activateDenyFeedback() {
  digitalWrite(Pins::kLedDenied, HIGH);
  digitalWrite(Pins::kBuzzer, HIGH);
  deny_feedback_active = true;
  deny_feedback_started_ms = millis();
}

void updateOutputs() {
  unsigned long now = millis();
  if (relay_active && now - relay_started_ms >= kAccessOpenDurationMs) {
    digitalWrite(Pins::kRelay, LOW);
    digitalWrite(Pins::kLedGranted, LOW);
    relay_active = false;
  }

  if (deny_feedback_active && now - deny_feedback_started_ms >= kStatusPulseMs) {
    digitalWrite(Pins::kLedDenied, LOW);
    digitalWrite(Pins::kBuzzer, LOW);
    deny_feedback_active = false;
  }
}

bool readRfidTag(String& uid_hex) {
  if (!mfrc522.PICC_IsNewCardPresent()) {
    return false;
  }
  if (!mfrc522.PICC_ReadCardSerial()) {
    return false;
  }

  if (mfrc522.uid.size != 4) {
    appendLocalLog("tag-no-soportado",
                   "Se detecto UID de longitud distinta a 4 bytes");
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
    return false;
  }

  char tag_buffer[9];
  snprintf(tag_buffer, sizeof(tag_buffer), "%02X%02X%02X%02X", mfrc522.uid.uidByte[0],
           mfrc522.uid.uidByte[1], mfrc522.uid.uidByte[2], mfrc522.uid.uidByte[3]);
  uid_hex = String(tag_buffer);

  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
  return true;
}

String buildAccessPayload(const String& tag_rfid) {
  StaticJsonDocument<256> document;
  document["tag_rfid"] = tag_rfid;
  document["node_id"] = node_config.node_id;
  document["timestamp_utc"] = currentTimestampUtc();

  String serialized;
  serializeJson(document, serialized);
  return serialized;
}

void processAccessResult(const String& tag_rfid, const ApiResult& response) {
  setState(FirmwareState::Procesando_Respuesta);

  if (response.auth_error) {
    auth_locked = true;
    node_authenticated = false;
    setState(FirmwareState::Error_Auth);
    appendLocalLog("error-autenticacion", "HTTP 401 al reportar tag " + tag_rfid);
    return;
  }

  if (response.timed_out) {
    setState(FirmwareState::Timeout_Local);
    appendLocalLog("timeout", "Sin respuesta dentro de " + String(node_config.timeout_ms) +
                                   " ms para tag " + tag_rfid);
    activateDenyFeedback();
    return;
  }

  if (response.success) {
    setState(FirmwareState::Actuando_Resultado);
    if (response.result == "autorizado") {
      appendLocalLog("autorizado", "Evento " + response.event_id + " para tag " + tag_rfid);
      activateAccessSignal();
    } else {
      appendLocalLog("denegado", response.code + " para tag " + tag_rfid);
      activateDenyFeedback();
    }
    return;
  }

  appendLocalLog("error-http", "HTTP " + String(response.http_code) + " para tag " + tag_rfid);
  activateDenyFeedback();
}

void postAccessEvent(const String& tag_rfid) {
  setState(FirmwareState::Enviando_Evento);
  const String payload = buildAccessPayload(tag_rfid);

  ApiResult response;
  for (uint8_t attempt = 0; attempt <= node_config.max_retries; ++attempt) {
    response = postJsonWithAuth("/access/events", payload, true);

    if (response.auth_error || response.timed_out || response.success) {
      break;
    }

    if (attempt < node_config.max_retries) {
      appendLocalLog("reintento",
                     "HTTP " + String(response.http_code) + ", intento " + String(attempt + 1) +
                         " de " + String(node_config.max_retries));
      delay(node_config.retry_interval_ms);
    }
  }

  processAccessResult(tag_rfid, response);
}

void ensureNodeAuthenticated() {
  if (auth_locked) {
    setState(FirmwareState::Esperando_Config);
    return;
  }

  if (node_authenticated) {
    return;
  }

  setState(FirmwareState::Autenticando_Nodo);
  if (sendHeartbeat()) {
    setState(FirmwareState::Operativo);
  }
}

void maybeSendHeartbeat() {
  if (auth_locked || !configLooksValid()) {
    return;
  }

  unsigned long interval_ms =
      static_cast<unsigned long>(node_config.heartbeat_interval_s) * 1000UL;
  unsigned long now = millis();
  if (now - last_heartbeat_attempt_ms < interval_ms) {
    return;
  }

  last_heartbeat_attempt_ms = now;
  sendHeartbeat();
}

void printPeriodicStatus() {
  unsigned long now = millis();
  if (now - last_status_print_ms < 10000UL) {
    return;
  }
  last_status_print_ms = now;
  String ip = WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : "-";

  Serial.printf("[STATUS] state=%s wifi=%s ip=%s auth=%s\n", stateName(current_state),
                WiFi.status() == WL_CONNECTED ? "on" : "off",
                ip.c_str(),
                node_authenticated ? "ok" : (auth_locked ? "locked" : "pending"));
}

}  // namespace

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(50);
  delay(500);

  setState(FirmwareState::Inicializando);
  configurePins();
  SPI.begin();
  mfrc522.PCD_Init();
  readPreferencesConfig();

  Serial.println("ESP32 RFID Access Node");
  printHelp();
  printConfig();

  if (!configLooksValid()) {
    appendLocalLog("config-incompleta",
                   "Completa la configuracion por serial y ejecuta 'save'");
    setState(FirmwareState::Esperando_Config);
    return;
  }

  ensureWiFiConnected();
}

void loop() {
  pollSerialConsole();
  updateOutputs();
  printPeriodicStatus();

  if (!configLooksValid()) {
    setState(FirmwareState::Esperando_Config);
    delay(25);
    return;
  }

  if (auth_locked) {
    setState(FirmwareState::Esperando_Config);
    delay(25);
    return;
  }

  if (!ensureWiFiConnected()) {
    delay(500);
    return;
  }

  ensureNodeAuthenticated();
  if (!node_authenticated) {
    delay(100);
    return;
  }

  maybeSendHeartbeat();

  setState(FirmwareState::Leyendo_RFID);
  String tag_rfid;
  if (readRfidTag(tag_rfid)) {
    postAccessEvent(tag_rfid);
    setState(FirmwareState::Operativo);
  } else if (current_state != FirmwareState::Operativo) {
    setState(FirmwareState::Operativo);
  }

  delay(20);
}
