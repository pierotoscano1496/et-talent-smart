"""0001_initial_schema

Migración inicial: crea todas las tablas e índices del sistema
IoT de Control de Acceso RFID.

Revision ID: 0001
Revises: (ninguna — es la migración base)
Create Date: 2025-01-01 00:00:00.000000

Requirements: 3.8, 6.1, 9.4
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Metadatos de revisión (requeridos por Alembic)
# ---------------------------------------------------------------------------
revision: str = "0001"
down_revision = None          # Primera migración, sin padre
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# upgrade: aplica la migración (crea tablas e índices)
# ---------------------------------------------------------------------------
def upgrade() -> None:
    # ------------------------------------------------------------------
    # Extensión pgcrypto para gen_random_uuid()
    # ------------------------------------------------------------------
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ------------------------------------------------------------------
    # Tabla: usuario_web
    # ------------------------------------------------------------------
    op.create_table(
        "usuario_web",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"),
                  nullable=False),
        sa.Column("nombre_completo", sa.String(100), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(60), nullable=False),
        sa.Column("rol", sa.String(20), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False,
                  server_default="activo"),
        sa.Column("primer_login", sa.Boolean(), nullable=False,
                  server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_usuario_web"),
        sa.UniqueConstraint("email", name="uq_usuario_web_email"),
    )

    # ------------------------------------------------------------------
    # Tabla: token_revocado
    # ------------------------------------------------------------------
    op.create_table(
        "token_revocado",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"),
                  nullable=False),
        sa.Column("jti", sa.Text(), nullable=False),
        sa.Column("revocado_en", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.Column("expira_en", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_token_revocado"),
        sa.UniqueConstraint("jti", name="uq_token_revocado_jti"),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario_web.id"],
            name="fk_token_revocado_usuario",
            ondelete="CASCADE",
        ),
    )

    # ------------------------------------------------------------------
    # Tabla: estudiante
    # ------------------------------------------------------------------
    op.create_table(
        "estudiante",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"),
                  nullable=False),
        sa.Column("nombre_completo", sa.String(100), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("grado_seccion", sa.String(20), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False,
                  server_default="activo"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_estudiante"),
        sa.UniqueConstraint("codigo", name="uq_estudiante_codigo"),
    )

    # ------------------------------------------------------------------
    # Tabla: tag_rfid
    # ------------------------------------------------------------------
    op.create_table(
        "tag_rfid",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"),
                  nullable=False),
        sa.Column("uid_hex", sa.String(8), nullable=False),
        sa.Column("estudiante_id", postgresql.UUID(as_uuid=True),
                  nullable=False),
        sa.Column("asignado_en", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.Column("desasignado_en", sa.TIMESTAMP(timezone=True),
                  nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False,
                  server_default=sa.text("TRUE")),
        sa.PrimaryKeyConstraint("id", name="pk_tag_rfid"),
        sa.UniqueConstraint("uid_hex", name="uq_tag_rfid_uid_hex"),
        sa.ForeignKeyConstraint(
            ["estudiante_id"], ["estudiante.id"],
            name="fk_tag_rfid_estudiante",
            ondelete="RESTRICT",
        ),
    )

    # ------------------------------------------------------------------
    # Tabla: ambiente
    # ------------------------------------------------------------------
    op.create_table(
        "ambiente",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"),
                  nullable=False),
        sa.Column("nombre", sa.String(80), nullable=False),
        sa.Column("descripcion", sa.String(255), nullable=False,
                  server_default=""),
        sa.Column("ubicacion", sa.String(120), nullable=False,
                  server_default=""),
        sa.Column("estado", sa.String(20), nullable=False,
                  server_default="activo"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ambiente"),
        sa.UniqueConstraint("nombre", name="uq_ambiente_nombre"),
    )

    # ------------------------------------------------------------------
    # Tabla: nodo_acceso
    # ------------------------------------------------------------------
    op.create_table(
        "nodo_acceso",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"),
                  nullable=False),
        sa.Column("identificador", sa.String(40), nullable=False),
        sa.Column("descripcion", sa.String(255), nullable=False,
                  server_default=""),
        sa.Column("estado", sa.String(20), nullable=False,
                  server_default="activo"),
        sa.Column("estado_conectividad", sa.String(20), nullable=False,
                  server_default="sin-conexion"),
        sa.Column("ultimo_heartbeat", sa.TIMESTAMP(timezone=True),
                  nullable=True),
        sa.Column("ambiente_id", postgresql.UUID(as_uuid=True),
                  nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_nodo_acceso"),
        sa.UniqueConstraint("identificador",
                            name="uq_nodo_acceso_identificador"),
        sa.ForeignKeyConstraint(
            ["ambiente_id"], ["ambiente.id"],
            name="fk_nodo_acceso_ambiente",
            ondelete="RESTRICT",
        ),
    )

    # ------------------------------------------------------------------
    # Tabla: token_nodo
    # ------------------------------------------------------------------
    op.create_table(
        "token_nodo",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"),
                  nullable=False),
        sa.Column("nodo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False,
                  server_default="activo"),
        sa.Column("generado_en", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.Column("revocado_en", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_token_nodo"),
        sa.UniqueConstraint("token_hash", name="uq_token_nodo_token_hash"),
        sa.ForeignKeyConstraint(
            ["nodo_id"], ["nodo_acceso.id"],
            name="fk_token_nodo_nodo",
            ondelete="CASCADE",
        ),
    )

    # ------------------------------------------------------------------
    # Tabla: evento_acceso
    # estudiante_id es nullable (NULL cuando el tag no está registrado)
    # ------------------------------------------------------------------
    op.create_table(
        "evento_acceso",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"),
                  nullable=False),
        sa.Column("tag_rfid", sa.String(8), nullable=False),
        sa.Column("nodo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ambiente_id", postgresql.UUID(as_uuid=True),
                  nullable=False),
        sa.Column("estudiante_id", postgresql.UUID(as_uuid=True),
                  nullable=True),
        sa.Column("timestamp_utc", sa.TIMESTAMP(timezone=True),
                  nullable=False),
        sa.Column("resultado", sa.String(20), nullable=False),
        sa.Column("codigo_resultado", sa.String(50), nullable=True),
        sa.Column("origen", sa.String(30), nullable=False,
                  server_default="nodo"),
        sa.PrimaryKeyConstraint("id", name="pk_evento_acceso"),
        sa.ForeignKeyConstraint(
            ["nodo_id"], ["nodo_acceso.id"],
            name="fk_evento_acceso_nodo",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ambiente_id"], ["ambiente.id"],
            name="fk_evento_acceso_ambiente",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["estudiante_id"], ["estudiante.id"],
            name="fk_evento_acceso_estudiante",
            ondelete="RESTRICT",
        ),
    )

    # ------------------------------------------------------------------
    # Tabla: bitacora_seguridad  (append-only, nunca se modifica)
    # ------------------------------------------------------------------
    op.create_table(
        "bitacora_seguridad",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"),
                  nullable=False),
        sa.Column("timestamp", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.Column("node_identifier", sa.String(40), nullable=False,
                  server_default=""),
        sa.Column("motivo_rechazo", sa.String(50), nullable=False),
        sa.Column("ip_origen", postgresql.INET(), nullable=True),
        sa.Column("detalle", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_bitacora_seguridad"),
    )

    # ------------------------------------------------------------------
    # Índices para rendimiento (Req 6.1)
    # ------------------------------------------------------------------

    # Consultas de reportes ordenadas por timestamp (más reciente primero)
    op.create_index(
        "idx_evento_acceso_timestamp",
        "evento_acceso",
        [sa.text("timestamp_utc DESC")],
    )

    # Monitoreo por nodo
    op.create_index(
        "idx_evento_acceso_nodo_timestamp",
        "evento_acceso",
        ["nodo_id", sa.text("timestamp_utc DESC")],
    )

    # Reportes por estudiante
    op.create_index(
        "idx_evento_acceso_estudiante_timestamp",
        "evento_acceso",
        ["estudiante_id", sa.text("timestamp_utc DESC")],
    )

    # Lookup rápido de tags activos durante procesamiento de acceso
    op.create_index(
        "idx_tag_rfid_uid_activo",
        "tag_rfid",
        ["uid_hex"],
        postgresql_where=sa.text("activo = TRUE"),
    )


# ---------------------------------------------------------------------------
# downgrade: revierte la migración (elimina tablas en orden inverso de FKs)
# ---------------------------------------------------------------------------
def downgrade() -> None:
    # Eliminar índices primero
    op.drop_index("idx_tag_rfid_uid_activo", table_name="tag_rfid")
    op.drop_index("idx_evento_acceso_estudiante_timestamp",
                  table_name="evento_acceso")
    op.drop_index("idx_evento_acceso_nodo_timestamp",
                  table_name="evento_acceso")
    op.drop_index("idx_evento_acceso_timestamp",
                  table_name="evento_acceso")

    # Eliminar tablas en orden inverso de dependencias FK
    op.drop_table("bitacora_seguridad")
    op.drop_table("evento_acceso")
    op.drop_table("token_nodo")
    op.drop_table("nodo_acceso")
    op.drop_table("ambiente")
    op.drop_table("tag_rfid")
    op.drop_table("estudiante")
    op.drop_table("token_revocado")
    op.drop_table("usuario_web")
