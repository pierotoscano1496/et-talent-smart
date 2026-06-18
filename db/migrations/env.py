"""
db/migrations/env.py
Entorno de ejecución de Alembic para el sistema IoT de Control de Acceso RFID.

Lee la URL de conexión desde la variable de entorno DATABASE_URL para evitar
credenciales en texto claro en archivos de configuración.
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Configuración de Alembic
# ---------------------------------------------------------------------------
config = context.config

# Configurar logging desde alembic.ini (si está disponible)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Inyectar la URL de base de datos desde la variable de entorno DATABASE_URL
# Ejemplo: postgresql://usuario:contraseña@postgres:5432/control_acceso
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL is None:
    raise RuntimeError(
        "La variable de entorno DATABASE_URL no está definida. "
        "Ejemplo: postgresql://user:pass@host:5432/dbname"
    )

config.set_main_option("sqlalchemy.url", DATABASE_URL)

# ---------------------------------------------------------------------------
# MetaData objetivo para migraciones 'autogenerate'
# Se puede importar Base.metadata de los modelos SQLAlchemy cuando estén listos
# ---------------------------------------------------------------------------
# from myapp.models import Base
# target_metadata = Base.metadata
target_metadata = None


# ---------------------------------------------------------------------------
# Modo offline: genera SQL sin conectarse a la base de datos
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo 'offline'.

    Configura el contexto solo con la URL, sin crear un Engine real.
    Permite generar el SQL de migración como script.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Modo online: se conecta a la base de datos y ejecuta las migraciones
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    """Ejecuta migraciones en modo 'online'.

    Crea un Engine, establece una conexión y ejecuta las migraciones
    dentro de una transacción.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Punto de entrada: seleccionar modo según contexto de ejecución
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
