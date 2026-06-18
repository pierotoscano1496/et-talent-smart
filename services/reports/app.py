"""
Application factory del Servicio_Reportes.

Crea y configura la instancia Flask con SQLAlchemy (solo lectura),
JWTManager y los blueprints de rutas.

Cumple: Requirements 9.3, 9.5
"""
import os

from flask import Flask

from authz import configure_jwt
from config import config_by_name
from extensions import db, jwt
from routes.health import health_bp
from routes.reports import reports_bp


def create_app(env: str | None = None) -> Flask:
    """Crea y retorna la aplicación Flask configurada."""
    if env is None:
        env = os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(env, config_by_name["default"]))

    # Inicializar extensiones
    db.init_app(app)
    jwt.init_app(app)
    configure_jwt(jwt)

    with app.app_context():
        import models  # noqa: F401

    # Registrar blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(reports_bp)

    return app
