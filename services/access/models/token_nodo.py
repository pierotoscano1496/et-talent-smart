"""
Modelo SQLAlchemy: TokenNodo

Almacena el hash SHA-256 del token de autenticación de cada nodo de acceso.
El token en texto claro nunca se persiste.

Tabla: token_nodo
Cumple: Requirements 8.1, 8.2, 8.3
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, TIMESTAMP, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db


class TokenNodo(db.Model):
    """Token de autenticación de un nodo de acceso (se almacena hash)."""

    __tablename__ = "token_nodo"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    nodo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodo_acceso.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True
    )
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="activo"
    )
    generado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    revocado_en: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Relación inversa con NodoAcceso
    nodo: Mapped["NodoAcceso"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "NodoAcceso",
        back_populates="tokens",
    )

    def __repr__(self) -> str:
        return f"<TokenNodo nodo_id={self.nodo_id} estado={self.estado}>"
