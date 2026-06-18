"""
Modelo de solo lectura para la tabla ambiente.
Cumple: Requirements 6.1, 6.2
"""
import uuid

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID

from extensions import db


class Ambiente(db.Model):
    """Representación de solo lectura de un ambiente educativo."""

    __tablename__ = "ambiente"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(80), nullable=False, unique=True)
    descripcion = Column(String(255), nullable=True)
    ubicacion = Column(String(120), nullable=True)
    estado = Column(String(20), nullable=False, default="activo")
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        """Serializa el ambiente a un diccionario JSON-serializable."""
        return {
            "id": str(self.id),
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "ubicacion": self.ubicacion,
            "estado": self.estado,
        }
