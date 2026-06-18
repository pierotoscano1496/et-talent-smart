"""
Modelo SQLAlchemy: EventoAcceso

Registro de cada lectura RFID procesada por el Servicio_Acceso.
El campo estudiante_id es nullable cuando el tag no está registrado.

Tabla: evento_acceso
Cumple: Requirements 3.4, 3.5, 3.6, 3.8, 2.7
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db


class EventoAcceso(db.Model):
    """Evento de acceso generado por la lectura de un tag RFID."""

    __tablename__ = "evento_acceso"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tag_rfid: Mapped[str] = mapped_column(String(8), nullable=False)
    nodo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodo_acceso.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ambiente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ambiente.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # nullable: NULL cuando el tag no está registrado en el sistema
    estudiante_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("estudiante.id", ondelete="RESTRICT"),
        nullable=True,
    )
    timestamp_utc: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    resultado: Mapped[str] = mapped_column(String(20), nullable=False)
    # nullable: NULL cuando el resultado es "autorizado"
    codigo_resultado: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    origen: Mapped[str] = mapped_column(
        String(30), nullable=False, default="nodo"
    )

    # Relaciones
    nodo: Mapped["NodoAcceso"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "NodoAcceso",
        back_populates="eventos",
    )
    estudiante: Mapped["Estudiante | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Estudiante",
        back_populates="eventos",
    )

    def __repr__(self) -> str:
        return (
            f"<EventoAcceso tag={self.tag_rfid} "
            f"resultado={self.resultado} ts={self.timestamp_utc}>"
        )
