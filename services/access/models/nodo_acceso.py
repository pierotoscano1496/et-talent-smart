"""
Modelo SQLAlchemy: NodoAcceso

Representa un nodo físico ESP32 + RC-522 instalado en la entrada
de un ambiente educativo.

Tabla: nodo_acceso
Cumple: Requirements 2.1, 2.3, 3.9
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db


class NodoAcceso(db.Model):
    """Nodo de acceso físico (ESP32 + RC-522)."""

    __tablename__ = "nodo_acceso"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    identificador: Mapped[str] = mapped_column(
        String(40), nullable=False, unique=True
    )
    descripcion: Mapped[str] = mapped_column(
        String(255), nullable=False, default=""
    )
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="activo"
    )
    estado_conectividad: Mapped[str] = mapped_column(
        String(20), nullable=False, default="sin-conexion"
    )
    ultimo_heartbeat: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    ambiente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ambiente.id", ondelete="RESTRICT"),
        nullable=False,
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
    ambiente: Mapped["Ambiente"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Ambiente",
        back_populates="nodos_acceso",
    )
    tokens: Mapped[list["TokenNodo"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "TokenNodo",
        back_populates="nodo",
        cascade="all, delete-orphan",
    )
    eventos: Mapped[list["EventoAcceso"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "EventoAcceso",
        back_populates="nodo",
    )

    def __repr__(self) -> str:
        return f"<NodoAcceso {self.identificador} estado={self.estado}>"
