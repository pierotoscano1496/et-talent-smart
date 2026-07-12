# TALENT SMART Beta

Instrucciones:

1. Cargar la web:

    ```bash
    npm run dev
    ```

2. Usar *NGROK* para publicar la página y hacerla pública:

    ```bash
    ngrok http 3000
    ```

    Mostrará el link para acceder desde internet, por ejemplo:

    ```Markdown
    https://tifany-coxal-unpresidentially.ngrok-free.dev/
    ```

    **Este directorio se usará para el código dell ESP32**

3. Cargar el código en **esp32.cpp** al ESP32, indicar en el código las credenciales de la red:

    ```C++
    const char* WIFI_SSID = "NOMBRE DE RED";
    const char* WIFI_PASSWORD = "CONTRASEÑA DE RED";
    ```

    Además la dirección del frontend en las líneas:

    ```C++
    const char* SERVER_URL = "https://<DIRECTORIO NGROK>/api/rfid/registro";
    const char* SERVER_CLOSE_URL = "https://<DIRECTORIO NGROK>/api/puerta/cerrar";
    ```

    Posteriormente indicar el nodo (ambiente) al que realizará el control. Ejemplo:

    ```C++
    const char* DEVICE_ID = "ESP32C6_RFID_01";
    const char* LOCATION_ID = "PUERTA_PRINCIPAL";
    ```

4. En el archivo **database.json** están la información de los datos que se irán grabando cuando se interactúe con el sistema.