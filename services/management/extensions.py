"""
Instancias de extensiones Flask compartidas en el Servicio_Gestion.
Se inicializan con el patrón app factory (init_app).
"""
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

# Instancia única de SQLAlchemy — importar desde aquí en los modelos
db: SQLAlchemy = SQLAlchemy()

# JWTManager para verificar tokens de usuarios web en endpoints protegidos
jwt: JWTManager = JWTManager()
