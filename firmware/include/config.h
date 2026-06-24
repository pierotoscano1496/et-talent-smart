#pragma once

#include <Arduino.h>

struct NodeConfig {
  char wifi_ssid[64];
  char wifi_password[64];
  char backend_url[128];
  char node_id[41];
  char node_token[256];
  uint16_t timeout_ms;
  uint8_t max_retries;
  uint16_t retry_interval_ms;
  uint16_t heartbeat_interval_s;
};

constexpr char kPreferencesNamespace[] = "nodecfg";
constexpr bool kDevAllowInsecureTls = true;

inline NodeConfig defaultNodeConfig() {
  NodeConfig config{};
  config.wifi_ssid[0] = '\0';
  config.wifi_password[0] = '\0';
  config.backend_url[0] = '\0';
  config.node_id[0] = '\0';
  config.node_token[0] = '\0';
  config.timeout_ms = 2000;
  config.max_retries = 3;
  config.retry_interval_ms = 5000;
  config.heartbeat_interval_s = 60;
  return config;
}
