"""
Modelo SQLAlchemy: BitacoraSeguridad

Registro append-only de intentos de acceso con token de nodo inválido.
Esta tabla nunca se actualiza ni se eliminan sus registros.

Campos:
  id              — UUID primario
  timestamp       — Momento del intento (UTC)
  node_identifier — Identificador del nodo si fue identificable, "" si no
  motivo_rechazo  — 'token-ausente' | 'token-malformado' | 'token-revocado'
  ip_origen       — Dirección IP del solicitante (INET de PostgreSQL)
  detalle         — Información adicional opcional (texto libre)

Tabla: bitacora_seguridad
Cumple: Requirements 8.1, 8.2
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, TIMESTAMP, Text
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db


class BitacoraSeguridad(db.Model):
    """Entrada append-only en la bitácora de seguridad."""

    __tablename__ = "bitacora_seguridad"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    # "" cuando el nodo no pudo identificarse a partir de la solicitud
    node_identifier: Mapped[str] = mapped_column(
        String(40), nullable=False, default=""
    )
    # Valores posibles: 'token-ausente', 'token-malformado', 'token-revocado'
    motivo_rechazo: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    ip_origen: Mapped[str | None] = mapped_column(
        INET, nullable=True
    )
    detalle: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<BitacoraSeguridad ts={self.timestamp} "
            f"motivo={self.motivo_rechazo} node={self.node_identifier}>"
        )
