# Instrucciones de pagina-control

La guía vigente está en [README.md](README.md). Este subproyecto integra el ESP32 RFID y su panel con Django/PostgreSQL; Talentosito es el otro subproyecto de robótica, dedicado a consultas.

Desde la raíz ejecutar `node deploy/dev.mjs start` y abrir http://localhost:3000/. Configurar el firmware mediante `secrets.example.h` según la guía. Para qa seguir [despliegue-qa.md](../docs/despliegue-qa.md).

Las antiguas instrucciones de Express, simulaciones web y persistencia en `database.json` dejan de aplicar. El archivo histórico se conserva sin importación automática.
