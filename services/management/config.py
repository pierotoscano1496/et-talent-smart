"""
Configuración del Servicio_Gestion.
Lee variables de entorno con fallbacks para desarrollo local.
"""
import os


class Config:
    # Base de datos — misma URI que Servicio_Autenticacion (instancia compartida)
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL",
        "postgresql://acceso_user:acceso_pass@localhost:5432/acceso_db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    # pool_pre_ping detecta conexiones muertas antes de usarlas (Req 9.5)
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_pre_ping": True,
    }

    # JWT — mismo secret que el resto de servicios para poder verificar tokens
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "dev-secret-key-change-in-prod")
    JWT_ALGORITHM: str = "HS256"
    BCRYPT_COST: int = int(os.environ.get("BCRYPT_COST", 12))

    # Puerto del servicio
    PORT: int = int(os.environ.get("PORT", 5003))

    # Entorno
    FLASK_ENV: str = os.environ.get("FLASK_ENV", "production")
    DEBUG: bool = FLASK_ENV == "development"
