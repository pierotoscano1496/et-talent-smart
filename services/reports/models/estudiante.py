"""
Modelo de solo lectura para la tabla estudiante.
Cumple: Requirements 6.1, 6.2
"""
import uuid

from sqlalchemy import Column, String, DateTime

from sqlalchemy.dialects.postgresql import UUID

from extensions import db


class Estudiante(db.Model):
    """Representación de solo lectura de un estudiante."""

    __tablename__ = "estudiante"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre_completo = Column(String(100), nullable=False)
    codigo = Column(String(20), nullable=False, unique=True)
    grado_seccion = Column(String(20), nullable=True)
    estado = Column(String(20), nullable=False, default="activo")
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        """Serializa el estudiante a un diccionario JSON-serializable."""
        return {
            "id": str(self.id),
            "nombre_completo": self.nombre_completo,
            "codigo": self.codigo,
            "grado_seccion": self.grado_seccion,
            "estado": self.estado,
        }
