"""
Application factory para el Servicio_Acceso.

Crea y configura la instancia Flask usando el patrón factory (create_app),
lo que facilita pruebas unitarias y despliegue en múltiples entornos.

Cumple: Requirements 8.1, 8.2, 9.3, 9.5
"""
import os

from flask import Flask

from auth.web_roles import configure_jwt
from config import config_by_name
from extensions import db, jwt
from heartbeat import configure_heartbeat_monitor
from routes.health import health_bp
from routes.access import access_bp


def create_app(config_name: str | None = None) -> Flask:
    """
    Crea y configura la aplicación Flask del Servicio_Acceso.

    Args:
        config_name: Nombre del entorno de configuración
                     ('development', 'production' o None para usar la
                     variable de entorno FLASK_ENV / 'default').

    Returns:
        Instancia de Flask completamente configurada.
    """
    app = Flask(__name__)

    # Determinar entorno de configuración
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    app.config.from_object(
        config_by_name.get(config_name, config_by_name["default"])
    )

    # Inicializar SQLAlchemy con pool_pre_ping habilitado (configurado en Config)
    db.init_app(app)

    with app.app_context():
        import models  # noqa: F401

    # Inicializar JWTManager (para endpoints protegidos de usuario web)
    jwt.init_app(app)
    configure_jwt(jwt)

    # Registrar blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(access_bp)
    configure_heartbeat_monitor(app)

    return app
