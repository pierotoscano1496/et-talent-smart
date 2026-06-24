#pragma once

#include <Arduino.h>

namespace Pins {
constexpr uint8_t kRfidSda = 5;
constexpr uint8_t kRfidRst = 27;
constexpr uint8_t kRelay = 26;
constexpr uint8_t kLedGranted = 2;
constexpr uint8_t kLedDenied = 4;
constexpr uint8_t kBuzzer = 15;
}  // namespace Pins
