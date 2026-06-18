"""
Helpers de autenticación/autorización para Servicio_Gestion.
"""
from __future__ import annotations

from functools import wraps

from flask import jsonify
from flask_jwt_extended import JWTManager, get_jwt, jwt_required

from extensions import db
from models.token_revocado import TokenRevocado


def configure_jwt(jwt_manager: JWTManager) -> None:
    """Registra callbacks JWT comunes para validación y revocación."""

    @jwt_manager.token_in_blocklist_loader
    def is_token_revoked(_jwt_header, jwt_payload) -> bool:
        jti = jwt_payload.get("jti")
        if not jti:
            return True
        token = (
            db.session.query(TokenRevocado)
            .filter(TokenRevocado.jti == jti)
            .first()
        )
        return token is not None

    @jwt_manager.revoked_token_loader
    def revoked_token_callback(_jwt_header, _jwt_payload):
        return jsonify({"error": "token-revocado"}), 401

    @jwt_manager.expired_token_loader
    def expired_token_callback(_jwt_header, _jwt_payload):
        return jsonify({"error": "token-expirado"}), 401

    @jwt_manager.invalid_token_loader
    def invalid_token_callback(_error: str):
        return jsonify({"error": "token-invalido"}), 401

    @jwt_manager.unauthorized_loader
    def unauthorized_callback(_error: str):
        return jsonify({"error": "token-invalido"}), 401


def roles_required(*allowed_roles: str):
    """Exige JWT válido y que el claim rol pertenezca a la lista permitida."""

    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            rol = get_jwt().get("rol")
            if rol not in allowed_roles:
                return jsonify({"error": "forbidden"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator
