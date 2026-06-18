"""
Extensiones Flask del Servicio_Acceso.

Las instancias se crean aquí sin asociarlas a ninguna aplicación (patrón
application factory). Se inicializan en create_app() mediante init_app().
"""
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

# Instancia de SQLAlchemy compartida entre todos los modelos del servicio
db: SQLAlchemy = SQLAlchemy()

# Instancia de JWTManager para validar tokens JWT de usuarios web
jwt: JWTManager = JWTManager()
