"""
Modelo SQLAlchemy: NodoAcceso

Representa un nodo físico ESP32 + RC-522 instalado en la entrada de un ambiente.
Incluye el estado operativo y el estado de conectividad (heartbeat).

Se mapea a la tabla `nodo_acceso` definida en db/init.sql.

Requirements: 2.3, 3.9
"""
from sqlalchemy import Column, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from extensions import db


class NodoAcceso(db.Model):
    __tablename__ = "nodo_acceso"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    # Identificador alfanumérico único, máximo 40 caracteres
    identificador = Column(String(40), nullable=False, unique=True)
    descripcion = Column(String(255), nullable=False, server_default="")
    # Estado operativo: "activo" | "inactivo"
    estado = Column(String(20), nullable=False, server_default="activo")
    # Estado de conectividad: "en-linea" | "sin-conexion"
    estado_conectividad = Column(
        String(20), nullable=False, server_default="sin-conexion"
    )
    # Timestamp del último heartbeat recibido
    ultimo_heartbeat = Column(TIMESTAMP(timezone=True), nullable=True)
    # FK al ambiente que controla este nodo
    ambiente_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ambiente.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )

    # Ambiente al que pertenece este nodo
    ambiente = relationship("Ambiente", back_populates="nodos_acceso")

    # Tokens de autenticación del nodo
    tokens = relationship(
        "TokenNodo",
        back_populates="nodo",
        lazy="select",
    )

    # Eventos de acceso generados por este nodo (solo lectura para reportes)
    eventos_acceso = relationship(
        "EventoAcceso",
        back_populates="nodo",
        lazy="dynamic",
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "identificador": self.identificador,
            "descripcion": self.descripcion,
            "estado": self.estado,
            "estado_conectividad": self.estado_conectividad,
            "ultimo_heartbeat": (
                self.ultimo_heartbeat.isoformat() if self.ultimo_heartbeat else None
            ),
            "ambiente_id": str(self.ambiente_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<NodoAcceso {self.identificador} estado={self.estado}>"
