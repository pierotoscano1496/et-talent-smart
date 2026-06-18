"""
Modelo SQLAlchemy: TokenNodo

Almacena el hash del token de autenticación de un nodo de acceso.
El token en texto claro nunca se persiste; solo se guarda el hash para
verificación segura.

Se mapea a la tabla `token_nodo` definida en db/init.sql.

Requirements: 8.3
"""
from sqlalchemy import Column, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from extensions import db


class TokenNodo(db.Model):
    __tablename__ = "token_nodo"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    # FK al nodo al que pertenece este token
    nodo_id = Column(
        UUID(as_uuid=True),
        ForeignKey("nodo_acceso.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Hash del token (SHA-256 o bcrypt), único en la tabla
    token_hash = Column(Text, nullable=False, unique=True)
    # Estado: "activo" | "revocado"
    estado = Column(String(20), nullable=False, server_default="activo")
    generado_en = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    # Fecha de revocación — NULL mientras el token está activo
    revocado_en = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relación con NodoAcceso
    nodo = relationship("NodoAcceso", back_populates="tokens")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "nodo_id": str(self.nodo_id),
            "estado": self.estado,
            "generado_en": self.generado_en.isoformat() if self.generado_en else None,
            "revocado_en": self.revocado_en.isoformat() if self.revocado_en else None,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TokenNodo nodo={self.nodo_id} estado={self.estado}>"
