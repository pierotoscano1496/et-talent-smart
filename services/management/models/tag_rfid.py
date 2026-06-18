"""
Modelo SQLAlchemy: TagRFID

Registra los tags RFID y su historial de asignación a estudiantes.
Un tag puede ser reasignado; el historial se conserva mediante el campo `activo`
y `desasignado_en`.

Se mapea a la tabla `tag_rfid` definida en db/init.sql.

Requirements: 1.2, 1.4
"""
from sqlalchemy import Boolean, Column, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from extensions import db


class TagRFID(db.Model):
    __tablename__ = "tag_rfid"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    # UID hexadecimal del tag, 8 caracteres, único en la tabla
    uid_hex = Column(String(8), nullable=False, unique=True)
    estudiante_id = Column(
        UUID(as_uuid=True),
        ForeignKey("estudiante.id", ondelete="RESTRICT"),
        nullable=False,
    )
    asignado_en = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    # Fecha de desasignación — NULL mientras el tag está activo
    desasignado_en = Column(TIMESTAMP(timezone=True), nullable=True)
    # True = tag actualmente activo y operativo
    activo = Column(Boolean, nullable=False, server_default="true")

    # Relación con Estudiante
    estudiante = relationship("Estudiante", back_populates="tags_rfid")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "uid_hex": self.uid_hex,
            "estudiante_id": str(self.estudiante_id),
            "asignado_en": self.asignado_en.isoformat() if self.asignado_en else None,
            "desasignado_en": self.desasignado_en.isoformat() if self.desasignado_en else None,
            "activo": self.activo,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TagRFID {self.uid_hex} activo={self.activo}>"
