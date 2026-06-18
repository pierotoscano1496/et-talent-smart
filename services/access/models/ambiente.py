"""
Modelo SQLAlchemy: Ambiente.

Representa el ambiente fisico asociado a los nodos del Servicio_Acceso.
"""

from sqlalchemy import Column, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import relationship

from extensions import db


class Ambiente(db.Model):
    __tablename__ = "ambiente"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    nombre = Column(String(80), nullable=False, unique=True)
    descripcion = Column(String(255), nullable=False, server_default="")
    ubicacion = Column(String(120), nullable=False, server_default="")
    estado = Column(String(20), nullable=False, server_default="activo")
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )

    nodos_acceso = relationship(
        "NodoAcceso",
        back_populates="ambiente",
        lazy="select",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Ambiente {self.nombre}>"
