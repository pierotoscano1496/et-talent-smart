"""
Modelo SQLAlchemy: Ambiente

Representa un espacio físico educativo (aula, laboratorio, etc.)
controlado por uno o más nodos de acceso.

Se mapea a la tabla `ambiente` definida en db/init.sql.

Requirements: 2.1
"""
from sqlalchemy import Column, String, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from extensions import db


class Ambiente(db.Model):
    __tablename__ = "ambiente"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    # Nombre único del ambiente, máximo 80 caracteres
    nombre = Column(String(80), nullable=False, unique=True)
    descripcion = Column(String(255), nullable=False, server_default="")
    ubicacion = Column(String(120), nullable=False, server_default="")
    # Estado: "activo" | "inactivo"
    estado = Column(String(20), nullable=False, server_default="activo")
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )

    # Nodos de acceso instalados en este ambiente
    nodos_acceso = relationship(
        "NodoAcceso",
        back_populates="ambiente",
        lazy="select",
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "ubicacion": self.ubicacion,
            "estado": self.estado,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Ambiente {self.nombre}>"
