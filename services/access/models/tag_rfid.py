"""
Modelo SQLAlchemy: TagRFID

Tag RFID asociado a un estudiante. Mantiene historial completo mediante
los campos activo y desasignado_en, permitiendo reasignación sin pérdida
de datos históricos.

Tabla: tag_rfid
Cumple: Requirements 1.2, 1.4
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, TIMESTAMP, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db


class TagRFID(db.Model):
    """Tag RFID embebido en la pulsera de un estudiante."""

    __tablename__ = "tag_rfid"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    uid_hex: Mapped[str] = mapped_column(
        String(8), nullable=False, unique=True
    )
    estudiante_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("estudiante.id", ondelete="RESTRICT"),
        nullable=False,
    )
    asignado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    desasignado_en: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relación inversa con Estudiante
    estudiante: Mapped["Estudiante"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Estudiante",
        back_populates="tags",
    )

    def __repr__(self) -> str:
        return f"<TagRFID uid={self.uid_hex} activo={self.activo}>"
