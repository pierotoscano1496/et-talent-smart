"""Utilidades de seguridad del Servicio_Gestion."""

from __future__ import annotations

import bcrypt
from flask import current_app


def hash_password(plain: str) -> str:
    """Genera un hash bcrypt usando el costo configurado."""
    rounds = int(current_app.config.get("BCRYPT_COST", 12))
    hashed = bcrypt.hashpw(
        plain.encode("utf-8"),
        bcrypt.gensalt(rounds=rounds),
    )
    return hashed.decode("utf-8")
