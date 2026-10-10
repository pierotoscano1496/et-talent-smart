# Talent Smart

Aplicación escolar con frontend React, API Django, PostgreSQL, MinIO y dos subproyectos de robótica: Talentosito (consultas por voz) y iot (asistencia RFID + ESP32).

- [Ejecutar dev](docs/ejecucion-dev.md)
- [Desplegar qa](docs/despliegue-qa.md)
- [Contrato de API e integración electrónica](docs/api.md)
- [Validación realizada y pendientes externos](docs/validacion.md)
- [Arquitectura](frontend/specs/arquitectura_sistema.md)
- [Casos de uso](frontend/specs/casos_uso_1.md)

Desde la raíz, con Node.js 24 y Docker Desktop/Engine activo:

```sh
node deploy/dev.mjs start
node deploy/dev.mjs admin
node deploy/dev.mjs test
```

Frontend: http://localhost:5173/et-talent-smart/ · API y administración: http://localhost:8000/admin/

El acceso web usa cuentas reales creadas por el administrador. No hay contraseñas predeterminadas. La sesión se conserva solo en memoria y requiere volver a ingresar al recargar la página.

El frontend ofrece inicio de sesión, consulta de horarios y asistencias, filtros y descarga CSV para auxiliar/docente. La gestión de usuarios, horarios e incidencias se encuentra disponible por API; el superusuario dispone también del admin de Django. Las demás pantallas de gestión específicas por rol y los módulos de notas/comunicados siguen pendientes.

Talentosito atiende consultas de los alumnos. [iot](iot/README.md) es la capa IoT: firmware ESP32 + RC522, sensor y servo, conectado directamente a Django. Se carga por USB en la placa; no tiene web ni contenedor. La aplicación escolar permanece en frontend/backend y PostgreSQL es su fuente de datos.

No se ha publicado qa desde esta implementación: requiere preparar Hostinger, dominios/TLS y secretos de Actions siguiendo la guía.
