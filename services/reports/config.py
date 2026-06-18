"""
Configuración del Servicio_Reportes.
Lee variables de entorno para DATABASE_URL, JWT_SECRET_KEY y límites de reportes.
"""
import os


class Config:
    """Configuración base leída desde variables de entorno."""

    # Base de datos (mismo URI que otros servicios; solo lectura por convención)
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
        # Modo solo lectura por convención: no se emite ninguna escritura desde este servicio.
        # Se puede reforzar en PostgreSQL otorgando al usuario solo privilegios SELECT.
        "execution_options": {"isolation_level": "READ COMMITTED"},
    }

    # JWT (solo validación; este servicio no emite tokens)
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-in-production")
    JWT_ALGORITHM: str = "HS256"

    # Límites de reportes
    REPORT_MAX_DAYS: int = int(os.environ.get("REPORT_MAX_DAYS", "90"))
    REPORT_MAX_ROWS: int = int(os.environ.get("REPORT_MAX_ROWS", "10000"))


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
