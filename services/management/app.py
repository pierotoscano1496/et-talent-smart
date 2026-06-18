"""
Application factory para el Servicio_Gestion.

Crea y configura la instancia Flask usando el patrón factory (create_app),
facilitando pruebas unitarias y despliegue en múltiples entornos.

Cumple: Requirements 1.1, 2.1, 7.1, 9.3, 9.5
"""
import os

from flask import Flask

from authz import configure_jwt
from config import Config
from extensions import db, jwt
from routes.health import health_bp
from routes.management import (
    students_bp,
    environments_bp,
    nodes_bp,
    users_bp,
)


def create_app(config_object: object | None = None) -> Flask:
    """
    Crea y configura la aplicación Flask del Servicio_Gestion.

    Args:
        config_object: Objeto de configuración a cargar directamente.
                       Si es None, se utiliza Config (lee variables de entorno).

    Returns:
        Instancia de Flask completamente configurada.
    """
    app = Flask(__name__)

    # Cargar configuración: objeto explícito o Config por defecto
    if config_object is None:
        app.config.from_object(Config)
    else:
        app.config.from_object(config_object)

    # Inicializar extensiones (sin app en la creación de instancias)
    db.init_app(app)
    jwt.init_app(app)
    configure_jwt(jwt)

    # Registrar modelos para que SQLAlchemy los conozca
    with app.app_context():
        import models  # noqa: F401

    # Registrar blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(environments_bp)
    app.register_blueprint(nodes_bp)
    app.register_blueprint(users_bp)

    return app
