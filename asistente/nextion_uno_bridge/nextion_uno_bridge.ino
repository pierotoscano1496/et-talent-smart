#include <SoftwareSerial.h>

// ESP32 -> Arduino Uno. Solo se necesita RX en el Uno para recibir estados.
#define ESP_RX_PIN 8
#define ESP_TX_PIN 9
#define ESP_BAUD 9600

// La Nextion usa Serial hardware del Uno: D1/TX -> RX Nextion, D0/RX <- TX Nextion.
#define NEXTION_BAUD 9600

SoftwareSerial espLink(ESP_RX_PIN, ESP_TX_PIN);
String incomingLine = "";

struct FaceRoute {
  const char* state;
  const char* nextionCommand;
};

FaceRoute faceRoutes[] = {
  {"BOOT", "page inicio"},
  {"IDLE", "page inicio"},
  {"LISTENING", "page escuchando"},
  {"THINKING", "page pensando"},
  {"SPEAKING", "page respondiendo"},
  {"ERROR", "page error"}
};

const size_t FACE_ROUTE_COUNT = sizeof(faceRoutes) / sizeof(faceRoutes[0]);

void endNextionCommand() {
  Serial.write(0xFF);
  Serial.write(0xFF);
  Serial.write(0xFF);
}

void sendNextionCommand(const char* command) {
  Serial.print(command);
  endNextionCommand();
}

void showFace(const String& state) {
  for (size_t i = 0; i < FACE_ROUTE_COUNT; i++) {
    if (state.equals(faceRoutes[i].state)) {
      sendNextionCommand(faceRoutes[i].nextionCommand);
      return;
    }
  }

  sendNextionCommand("page error");
}

void processEspLine(String line) {
  line.trim();
  line.toUpperCase();

  if (line.length() == 0) {
    return;
  }

  if (line.startsWith("FACE:")) {
    line.remove(0, 5);
  }

  showFace(line);
}

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(NEXTION_BAUD);
  espLink.begin(ESP_BAUD);

  delay(500);
  sendNextionCommand("page inicio");
}

void loop() {
  while (espLink.available()) {
    const char incoming = static_cast<char>(espLink.read());

    if (incoming == '\n') {
      processEspLine(incomingLine);
      incomingLine = "";
      digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
      continue;
    }

    if (incoming != '\r' && incomingLine.length() < 40) {
      incomingLine += incoming;
    }
  }
}
