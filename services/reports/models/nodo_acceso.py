"""
Modelo de solo lectura para la tabla nodo_acceso.
Cumple: Requirements 6.1, 6.2
"""
import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from extensions import db


class NodoAcceso(db.Model):
    """Representación de solo lectura de un nodo de acceso."""

    __tablename__ = "nodo_acceso"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identificador = Column(String(40), nullable=False, unique=True)
    descripcion = Column(String(255), nullable=True)
    estado = Column(String(20), nullable=False, default="activo")
    estado_conectividad = Column(String(20), nullable=True)
    ultimo_heartbeat = Column(DateTime(timezone=True), nullable=True)
    ambiente_id = Column(UUID(as_uuid=True), ForeignKey("ambiente.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        """Serializa el nodo a un diccionario JSON-serializable."""
        return {
            "id": str(self.id),
            "identificador": self.identificador,
            "descripcion": self.descripcion,
            "estado": self.estado,
            "estado_conectividad": self.estado_conectividad,
            "ultimo_heartbeat": (
                self.ultimo_heartbeat.isoformat() if self.ultimo_heartbeat else None
            ),
            "ambiente_id": str(self.ambiente_id) if self.ambiente_id else None,
        }
