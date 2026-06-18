"""
Modelo SQLAlchemy: Estudiante

Estudiante registrado en el sistema que porta una pulsera RFID.

Tabla: estudiante
Cumple: Requirements 1.1, 1.5, 1.6
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db


class Estudiante(db.Model):
    """Estudiante del sistema con pulsera RFID."""

    __tablename__ = "estudiante"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    nombre_completo: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    codigo: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True
    )
    grado_seccion: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="activo"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relaciones
    tags: Mapped[list["TagRFID"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "TagRFID",
        back_populates="estudiante",
    )
    eventos: Mapped[list["EventoAcceso"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "EventoAcceso",
        back_populates="estudiante",
    )

    def __repr__(self) -> str:
        return f"<Estudiante {self.codigo} {self.nombre_completo} estado={self.estado}>"
