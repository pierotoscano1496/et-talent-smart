#pragma once
const char* WIFI_SSID = "NOMBRE_DE_TU_WIFI";
const char* WIFI_PASSWORD = "PASSWORD_DE_TU_WIFI";
// Conexión directa a Django. qa: https://DOMINIO_API/api/...
const char* SERVER_URL = "http://IP_DE_TU_PC:8000/api/rfid/registro";
const char* SERVER_STATE_URL = "http://IP_DE_TU_PC:8000/api/puerta/estado";
// Copiar RFID_API_KEY del archivo privado del MISMO ambiente.
const char* API_KEY = "REEMPLAZAR_CON_RFID_API_KEY";
const char* DEVICE_ID = "ESP32C6_RFID_01";
const char* LOCATION_ID = "PUERTA_PRINCIPAL";
// Solo dev en red local. En qa cambiar a false y usar HTTPS.
const bool ALLOW_INSECURE_HTTP = true;
// En qa pegar el certificado PEM de la CA que firma el dominio de API.
// Nunca usar setInsecure(). HTTPS se rechaza si falta la CA o la hora NTP.
const char* TLS_ROOT_CA = R"PEM()PEM";
