#pragma once

enum class FirmwareState {
  Inicializando,
  Conectando_WiFi,
  Autenticando_Nodo,
  Operativo,
  Leyendo_RFID,
  Enviando_Evento,
  Procesando_Respuesta,
  Actuando_Resultado,
  Timeout_Local,
  Enviando_Heartbeat,
  Error_Auth,
  Esperando_Config,
};

inline const char* stateName(FirmwareState state) {
  switch (state) {
    case FirmwareState::Inicializando:
      return "Inicializando";
    case FirmwareState::Conectando_WiFi:
      return "Conectando_WiFi";
    case FirmwareState::Autenticando_Nodo:
      return "Autenticando_Nodo";
    case FirmwareState::Operativo:
      return "Operativo";
    case FirmwareState::Leyendo_RFID:
      return "Leyendo_RFID";
    case FirmwareState::Enviando_Evento:
      return "Enviando_Evento";
    case FirmwareState::Procesando_Respuesta:
      return "Procesando_Respuesta";
    case FirmwareState::Actuando_Resultado:
      return "Actuando_Resultado";
    case FirmwareState::Timeout_Local:
      return "Timeout_Local";
    case FirmwareState::Enviando_Heartbeat:
      return "Enviando_Heartbeat";
    case FirmwareState::Error_Auth:
      return "Error_Auth";
    case FirmwareState::Esperando_Config:
      return "Esperando_Config";
    default:
      return "Desconocido";
  }
}
