"""
Blueprint de autenticación para el Servicio_Autenticacion.

Contiene stubs de los endpoints de autenticación. La implementación
completa se realiza en las tareas 2.3, 2.4 y 2.5.

Endpoints registrados:
  POST /auth/login           — Valida credenciales y emite JWT (tarea 2.3)
  POST /auth/logout          — Revoca el JWT activo (tarea 2.4)
  POST /auth/change-password — Cambia la contraseña del usuario (tarea 2.5)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from extensions import db
from models.token_revocado import TokenRevocado
from models.usuario_web import UsuarioWeb
from utils.security import hash_password, verify_password

auth_bp = Blueprint("auth", __name__)


def _invalid_credentials():
    return jsonify({"error": "credenciales-invalidas"}), 401


def _invalid_data():
    return jsonify({"error": "datos-invalidos"}), 400


def _identity_as_uuid(raw_identity: str | None) -> uuid.UUID | None:
    if not raw_identity or not isinstance(raw_identity, str):
        return None
    try:
        return uuid.UUID(raw_identity)
    except ValueError:
        return None


def _find_user_by_email(email: str) -> UsuarioWeb | None:
    normalized = email.strip().lower()
    if not normalized:
        return None
    return (
        db.session.query(UsuarioWeb)
        .filter(func.lower(UsuarioWeb.email) == normalized)
        .first()
    )


@auth_bp.post("/auth/login")
def login():
    """
    Valida credenciales de usuario web y retorna un JWT firmado HS256.
    Implementa autenticación con JWT HS256 y respuesta genérica ante fallo.
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    if not isinstance(email, str) or not isinstance(password, str):
        return _invalid_data()

    user = _find_user_by_email(email)
    if user is None or user.estado != "activo":
        return _invalid_credentials()

    if not verify_password(password, user.password_hash):
        return _invalid_credentials()

    token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "rol": user.rol,
            "nombre": user.nombre_completo,
            "primer_login": user.primer_login,
        },
    )

    return jsonify(user.to_login_dict(token)), 200


@auth_bp.post("/auth/logout")
@jwt_required()
def logout():
    """
    Revoca el JWT activo del usuario autenticado.
    Revoca el JWT activo agregando su JTI a token_revocado.
    """
    jwt_payload = get_jwt()
    jti = jwt_payload.get("jti")
    exp = jwt_payload.get("exp")
    user_id = _identity_as_uuid(get_jwt_identity())

    if not jti or not exp or not user_id:
        return jsonify({"error": "token-invalido"}), 401

    token_revocado = TokenRevocado(
        jti=jti,
        expira_en=datetime.fromtimestamp(exp, tz=timezone.utc),
        usuario_id=user_id,
    )

    try:
        db.session.add(token_revocado)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"error": "error-interno"}), 500

    return jsonify({"mensaje": "sesion-cerrada"}), 200


@auth_bp.post("/auth/change-password")
@jwt_required()
def change_password():
    """
    Cambia la contraseña del usuario autenticado.
    Cambia la contraseña del usuario autenticado y limpia primer_login.
    """
    data = request.get_json(silent=True) or {}
    password_actual = data.get("password_actual", data.get("current_password"))
    password_nueva = data.get("password_nueva", data.get("new_password"))

    if not isinstance(password_actual, str) or not isinstance(password_nueva, str):
        return _invalid_data()

    password_actual = password_actual.strip()
    password_nueva = password_nueva.strip()
    if not password_actual or not password_nueva:
        return _invalid_data()

    user_id = _identity_as_uuid(get_jwt_identity())
    if user_id is None:
        return jsonify({"error": "token-invalido"}), 401

    user = db.session.get(UsuarioWeb, user_id)
    if user is None or user.estado != "activo":
        return _invalid_credentials()

    if not verify_password(password_actual, user.password_hash):
        return _invalid_credentials()

    user.password_hash = hash_password(password_nueva)
    user.primer_login = False
    user.updated_at = datetime.now(timezone.utc)

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"error": "error-interno"}), 500

    return jsonify({"mensaje": "contrasena-actualizada"}), 200
