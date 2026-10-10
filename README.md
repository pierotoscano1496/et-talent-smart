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

El acceso web usa cuentas creadas por el administrador. En dev, `node deploy/dev.mjs start` carga los datos de prueba después de las migraciones; también se pueden cargar con `node deploy/dev.mjs seed`. Sus credenciales y la inicialización SQL están en [ejecución dev](docs/ejecucion-dev.md). Qa no recibe estas cuentas. La sesión se conserva solo en memoria y requiere volver a ingresar al recargar la página.

El frontend muestra menús y acciones según el rol: cuentas y llaves para el administrador; asignaciones académicas, horarios y eventos para el coordinador; asistencia y retiros tempranos para el auxiliar; horario, asistencia y justificaciones para el docente; información propia o de hijos para estudiantes y padres. Los permisos también se validan en Django. Los módulos de notas, conducta y comunicados quedan fuera de esta implementación de los casos CU-01 a CU-07.

Talentosito atiende consultas de los alumnos. [iot](iot/README.md) es la capa IoT: firmware ESP32 + RC522, sensor y servo, conectado directamente a Django. Se carga por USB en la placa; no tiene web ni contenedor. La aplicación escolar permanece en frontend/backend y PostgreSQL es su fuente de datos.

No se ha publicado qa desde esta implementación: requiere preparar Hostinger, dominios/TLS y secretos de Actions siguiendo la guía.
