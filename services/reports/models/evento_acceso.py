"""
Modelo de solo lectura para la tabla evento_acceso.
Incluye relaciones a Estudiante y Ambiente para los reportes enriquecidos.
Cumple: Requirements 6.1, 6.2, 9.3
"""
import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from extensions import db


class EventoAcceso(db.Model):
    """Representación de solo lectura de un evento de acceso RFID."""

    __tablename__ = "evento_acceso"
    # No emitir CREATE TABLE desde este servicio; la tabla ya existe
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tag_rfid = Column(String(8), nullable=False)
    nodo_id = Column(UUID(as_uuid=True), ForeignKey("nodo_acceso.id"), nullable=False)
    ambiente_id = Column(UUID(as_uuid=True), ForeignKey("ambiente.id"), nullable=False)
    estudiante_id = Column(UUID(as_uuid=True), ForeignKey("estudiante.id"), nullable=True)
    timestamp_utc = Column(DateTime(timezone=True), nullable=False)
    resultado = Column(String(20), nullable=False)
    codigo_resultado = Column(String(50), nullable=True)
    origen = Column(String(30), nullable=True)

    # Relaciones de solo lectura para enriquecer reportes
    nodo = relationship("NodoAcceso", lazy="select", foreign_keys=[nodo_id])
    ambiente = relationship("Ambiente", lazy="select", foreign_keys=[ambiente_id])
    estudiante = relationship("Estudiante", lazy="select", foreign_keys=[estudiante_id])

    def to_dict(self) -> dict:
        """Serializa el evento a un diccionario JSON-serializable."""
        return {
            "id": str(self.id),
            "tag_rfid": self.tag_rfid,
            "nodo_id": str(self.nodo_id),
            "ambiente_id": str(self.ambiente_id),
            "estudiante_id": str(self.estudiante_id) if self.estudiante_id else None,
            "timestamp_utc": self.timestamp_utc.isoformat() if self.timestamp_utc else None,
            "resultado": self.resultado,
            "codigo_resultado": self.codigo_resultado,
            "origen": self.origen,
        }

    def to_report_dict(self) -> dict:
        """Serializa el evento al formato requerido por GET /reports/events."""
        ambiente_nombre = self.ambiente.nombre if self.ambiente else None
        estudiante_nombre = self.estudiante.nombre_completo if self.estudiante else None
        return {
            "evento_id": str(self.id),
            "tag_rfid": self.tag_rfid,
            "nodo_id": str(self.nodo_id),
            "ambiente_nombre": ambiente_nombre,
            "estudiante_nombre": estudiante_nombre,
            "timestamp_utc": self.timestamp_utc.isoformat() if self.timestamp_utc else None,
            "resultado": self.resultado,
            "codigo_resultado": self.codigo_resultado,
        }
