#pragma once
#include <Arduino.h>

// Ajustar el cableado a la placa seleccionada. Nunca usar GPIO 6-11 del
// ESP32 clásico: normalmente están conectados a la memoria flash.
#if defined(CONFIG_IDF_TARGET_ESP32C6)
constexpr uint8_t RFID_SCK = 6;
constexpr uint8_t RFID_MISO = 2;
constexpr uint8_t RFID_MOSI = 7;
constexpr uint8_t RFID_SS = 10;
constexpr uint8_t RFID_RST = 3;
constexpr uint8_t ULTRASONIC_TRIG = 18;
constexpr uint8_t ULTRASONIC_ECHO = 19;
constexpr uint8_t SERVO_PIN = 4;
#elif defined(CONFIG_IDF_TARGET_ESP32)
// ESP32 Dev Module / WROOM-32.
constexpr uint8_t RFID_SCK = 18;
constexpr uint8_t RFID_MISO = 19;
constexpr uint8_t RFID_MOSI = 23;
constexpr uint8_t RFID_SS = 21;
constexpr uint8_t RFID_RST = 22;
constexpr uint8_t ULTRASONIC_TRIG = 26;
constexpr uint8_t ULTRASONIC_ECHO = 27;
constexpr uint8_t SERVO_PIN = 25;
#else
#error "Selecciona ESP32 Dev Module o ESP32C6 Dev Module y revisa pins.h para tu circuito."
#endif
