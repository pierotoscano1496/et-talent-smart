"""
Modelo SQLAlchemy: EventoAcceso (referencia de solo lectura)

Este modelo se declara en el Servicio_Gestion únicamente para satisfacer
las relaciones SQLAlchemy definidas en Estudiante y NodoAcceso (e.g., para
cumplir con el Req 1.6 / 2.6: verificar que los eventos no se alteran al
desactivar una entidad).

La lógica de escritura de eventos vive en el Servicio_Acceso.

Se mapea a la tabla `evento_acceso` definida en db/init.sql.
"""
from sqlalchemy import Column, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from extensions import db


class EventoAcceso(db.Model):
    __tablename__ = "evento_acceso"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tag_rfid = Column(String(8), nullable=False)
    nodo_id = Column(
        UUID(as_uuid=True),
        ForeignKey("nodo_acceso.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ambiente_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ambiente.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # NULL cuando el tag no está registrado en el sistema
    estudiante_id = Column(
        UUID(as_uuid=True),
        ForeignKey("estudiante.id", ondelete="RESTRICT"),
        nullable=True,
    )
    timestamp_utc = Column(TIMESTAMP(timezone=True), nullable=False)
    resultado = Column(String(20), nullable=False)
    codigo_resultado = Column(String(50), nullable=True)
    origen = Column(String(30), nullable=False, server_default="nodo")

    # Relaciones de solo lectura
    estudiante = relationship("Estudiante", back_populates="eventos_acceso")
    nodo = relationship("NodoAcceso", back_populates="eventos_acceso")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<EventoAcceso {self.id} resultado={self.resultado}>"
