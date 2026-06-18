"""
Configuración del Servicio_Autenticacion.
Lee variables de entorno para DATABASE_URI, JWT_SECRET_KEY y BCRYPT_COST.
"""
import os
from datetime import timedelta


class Config:
    """Configuración base leída desde variables de entorno."""

    # Base de datos
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL",
        os.environ.get(
            "DATABASE_URI",
            "postgresql://postgres:postgres@localhost:5432/acceso_db",
        ),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_pre_ping": True,
    }

    # JWT
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.environ.get("JWT_EXPIRY_HOURS", "8"))
    )

    # Bcrypt
    BCRYPT_COST: int = int(os.environ.get("BCRYPT_COST", "12"))


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
