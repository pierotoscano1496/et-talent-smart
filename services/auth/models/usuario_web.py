"""
Modelo SQLAlchemy: UsuarioWeb

Representa a los usuarios del sistema web autenticados por el
Servicio_Autenticacion.
"""
from sqlalchemy import Boolean, Column, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

from extensions import db


class UsuarioWeb(db.Model):
    __tablename__ = "usuario_web"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    nombre_completo = Column(String(100), nullable=False)
    email = Column(String(254), nullable=False, unique=True)
    password_hash = Column(String(60), nullable=False)
    rol = Column(String(20), nullable=False)
    estado = Column(String(20), nullable=False, server_default="activo")
    primer_login = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )

    def to_login_dict(self, token: str) -> dict:
        """Serializa la respuesta de login sin exponer datos sensibles."""
        return {
            "token": token,
            "rol": self.rol,
            "nombre": self.nombre_completo,
            "primer_login": self.primer_login,
        }
