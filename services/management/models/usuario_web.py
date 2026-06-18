"""
Modelo SQLAlchemy: UsuarioWeb

Representa a los usuarios del sistema web (Administradores y Auxiliares).
Se mapea a la tabla `usuario_web` definida en db/init.sql.

Requirements: 7.1
"""
from sqlalchemy import Boolean, Column, String, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from extensions import db


class UsuarioWeb(db.Model):
    __tablename__ = "usuario_web"

    # Clave primaria UUID generada por PostgreSQL
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    nombre_completo = Column(String(100), nullable=False)
    email = Column(String(254), nullable=False, unique=True)
    password_hash = Column(String(60), nullable=False)
    # Rol: "ADMINISTRADOR" | "AUXILIAR_EDUCACION"
    rol = Column(String(20), nullable=False)
    # Estado: "activo" | "inactivo"
    estado = Column(String(20), nullable=False, server_default="activo")
    # True indica que el usuario aún no cambió su contraseña temporal
    primer_login = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )

    # Relación inversa con TokenRevocado (definida en el Servicio_Autenticacion;
    # aquí se omite para no duplicar lógica entre servicios).

    def to_dict(self) -> dict:
        """Serialización segura — excluye password_hash."""
        return {
            "id": str(self.id),
            "nombre_completo": self.nombre_completo,
            "email": self.email,
            "rol": self.rol,
            "estado": self.estado,
            "primer_login": self.primer_login,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UsuarioWeb {self.email} ({self.rol})>"
