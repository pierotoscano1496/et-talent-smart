"""
Modelo SQLAlchemy: Estudiante

Representa a los estudiantes registrados en el sistema.
Se mapea a la tabla `estudiante` definida en db/init.sql.

Requirements: 1.1
"""
from sqlalchemy import Column, String, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from extensions import db


class Estudiante(db.Model):
    __tablename__ = "estudiante"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    nombre_completo = Column(String(100), nullable=False)
    # Código alfanumérico único, máximo 20 caracteres
    codigo = Column(String(20), nullable=False, unique=True)
    grado_seccion = Column(String(20), nullable=False)
    # Estado: "activo" | "inactivo"
    estado = Column(String(20), nullable=False, server_default="activo")
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )

    # Tags RFID asociados a este estudiante (historial completo, incluyendo inactivos)
    tags_rfid = relationship(
        "TagRFID",
        back_populates="estudiante",
        lazy="select",
    )

    # Eventos de acceso asociados — relación de solo lectura para reportes
    eventos_acceso = relationship(
        "EventoAcceso",
        back_populates="estudiante",
        lazy="dynamic",
    )

    @property
    def tag_activo(self):
        """Retorna el TagRFID activo del estudiante, o None si no tiene."""
        return next((t for t in self.tags_rfid if t.activo), None)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "nombre_completo": self.nombre_completo,
            "codigo": self.codigo,
            "grado_seccion": self.grado_seccion,
            "estado": self.estado,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Estudiante {self.codigo} – {self.nombre_completo}>"
