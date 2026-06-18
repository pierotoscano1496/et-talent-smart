"""
Extensiones Flask del Servicio_Reportes.

Las instancias se crean aquí sin asociarlas a ninguna aplicación (patrón
application factory). Se inicializan en create_app() mediante init_app().

Este servicio opera en modo solo lectura: SQLAlchemy se configura con
isolation_level READ COMMITTED y no se emite ninguna escritura desde este
paquete. Para máxima garantía, el usuario de PostgreSQL empleado debe tener
únicamente privilegios SELECT sobre las tablas del esquema.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

# Instancia de SQLAlchemy — solo lectura por convención
db: SQLAlchemy = SQLAlchemy()

# Instancia de JWTManager — solo para validación de tokens (no emisión)
jwt: JWTManager = JWTManager()
