"""
Application factory para el Servicio_Autenticacion.

Crea y configura la instancia Flask usando el patrón factory (create_app),
lo que facilita pruebas unitarias y despliegue en múltiples entornos.

Cumple: Requirements 9.3, 9.5
"""
import os

from flask import Flask
from flask_jwt_extended import JWTManager

from config import config_by_name
from extensions import db, jwt
from models.token_revocado import TokenRevocado
from routes.auth import auth_bp
from routes.health import health_bp


def create_app(config_name: str | None = None) -> Flask:
    """
    Crea y configura la aplicación Flask.

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

    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Inicializar SQLAlchemy con pool_pre_ping habilitado (ya declarado en config)
    db.init_app(app)

    # Registrar modelos antes de usar callbacks o consultas
    with app.app_context():
        import models  # noqa: F401

    # Inicializar JWTManager
    jwt.init_app(app)

    _register_jwt_callbacks(jwt)

    # Registrar blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)

    return app


def _register_jwt_callbacks(jwt_manager: JWTManager) -> None:
    """Registra callbacks de validación y errores JWT."""

    @jwt_manager.token_in_blocklist_loader
    def is_token_revoked(_jwt_header, jwt_payload) -> bool:
        jti = jwt_payload.get("jti")
        if not jti:
            return True
        token = (
            db.session.query(TokenRevocado)
            .filter(TokenRevocado.jti == jti)
            .first()
        )
        return token is not None

    @jwt_manager.revoked_token_loader
    def revoked_token_callback(_jwt_header, _jwt_payload):
        return {"error": "token-revocado"}, 401

    @jwt_manager.expired_token_loader
    def expired_token_callback(_jwt_header, _jwt_payload):
        return {"error": "token-expirado"}, 401

    @jwt_manager.invalid_token_loader
    def invalid_token_callback(_error: str):
        return {"error": "token-invalido"}, 401

    @jwt_manager.unauthorized_loader
    def unauthorized_callback(_error: str):
        return {"error": "token-invalido"}, 401
