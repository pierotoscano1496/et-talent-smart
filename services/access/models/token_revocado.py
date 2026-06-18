"""
Modelo de solo lectura para la tabla token_revocado.
"""
from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

from extensions import db


class TokenRevocado(db.Model):
    __tablename__ = "token_revocado"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    jti = Column(Text, nullable=False, unique=True)
    revocado_en = Column(TIMESTAMP(timezone=True), nullable=False)
    expira_en = Column(TIMESTAMP(timezone=True), nullable=False)
    usuario_id = Column(
        UUID(as_uuid=True),
        ForeignKey("usuario_web.id", ondelete="CASCADE"),
        nullable=False,
    )
