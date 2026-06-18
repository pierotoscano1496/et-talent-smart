"""
Configuración del Servicio_Acceso.
Lee variables de entorno para DATABASE_URL, JWT_SECRET_KEY y parámetros
de heartbeat.

Cumple: Requirements 8.1, 8.2, 9.3, 9.5
"""
import os


class Config:
    """Configuración base leída desde variables de entorno."""

    # Base de datos
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/acceso_db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_pre_ping": True,
    }

    # JWT (para validar tokens de usuarios web en endpoints protegidos)
    JWT_SECRET_KEY: str = os.environ.get(
        "JWT_SECRET_KEY", "dev-secret-change-in-production"
    )
    JWT_ALGORITHM: str = "HS256"

    # Heartbeat
    HEARTBEAT_TIMEOUT_S: int = int(os.environ.get("HEARTBEAT_TIMEOUT_S", "120"))
    HEARTBEAT_CHECK_INTERVAL_S: int = int(
        os.environ.get("HEARTBEAT_CHECK_INTERVAL_S", "30")
    )


class DevelopmentConfig(Config):
    """Configuración para desarrollo local."""

    DEBUG: bool = True


class ProductionConfig(Config):
    """Configuración para producción."""

    DEBUG: bool = False


# Mapa de entornos
config_by_name: dict = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
