"""
Modelo SQLAlchemy: TokenRevocado

Lista negra de JWTs revocados por cierre de sesion.
"""
from sqlalchemy import Column, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

from extensions import db


class TokenRevocado(db.Model):
    __tablename__ = "token_revocado"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    jti = Column(Text, nullable=False, unique=True)
    revocado_en = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    expira_en = Column(TIMESTAMP(timezone=True), nullable=False)
    usuario_id = Column(
        UUID(as_uuid=True),
        ForeignKey("usuario_web.id", ondelete="CASCADE"),
        nullable=False,
    )
