"""
Decorador de autenticacion por token de nodo: node_token_required.

Mecanismo:
  1. Extrae la cabecera HTTP Authorization: Bearer <token>
  2. Computa el hash SHA-256 del token en texto claro
  3. Consulta la tabla token_nodo y carga el nodo propietario
  4. Si no se encuentra o hay algun problema:
       - Inserta un registro en bitacora_seguridad con timestamp, node_identifier
         (del body si esta disponible), motivo y ip_origen
       - Retorna HTTP 401 {"error": "token-nodo-invalido"}
  5. Si es valido: verifica que el node_id reportado coincida con el nodo del
     token, almacena TokenNodo en flask.g.nodo_token y NodoAcceso en
     flask.g.nodo_autenticado, y llama a la funcion decorada.

Motivos de rechazo registrados:
  - 'token-ausente' -> cabecera Authorization ausente o vacia
  - 'token-malformado' -> cabecera presente pero no sigue el formato Bearer <token>
  - 'token-revocado' -> hash encontrado pero estado != 'activo'
  - 'token-no-encontrado' -> hash no existe en token_nodo
  - 'token-nodo-no-coincide' -> el token pertenece a otro nodo

Cumple: Requirements 8.1, 8.2
"""

from __future__ import annotations

import hashlib
import logging
from functools import wraps
from typing import Callable

from flask import g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from extensions import db
from models.bitacora_seguridad import BitacoraSeguridad
from models.token_nodo import TokenNodo

logger = logging.getLogger(__name__)


def _get_ip_origen() -> str | None:
    """Determina la IP de origen de la solicitud."""
    return request.headers.get("X-Real-IP") or request.remote_addr or None


def _get_node_identifier_from_body() -> str:
    """Intenta extraer node_id del cuerpo JSON de la solicitud."""
    try:
        data = request.get_json(silent=True) or {}
        return str(data.get("node_id", "")).strip()[:40]
    except Exception:
        return ""


def _log_security_event(
    motivo: str,
    node_identifier: str = "",
    detalle: str | None = None,
) -> None:
    """Inserta un registro append-only en bitacora_seguridad."""
    try:
        entrada = BitacoraSeguridad(
            node_identifier=node_identifier,
            motivo_rechazo=motivo,
            ip_origen=_get_ip_origen(),
            detalle=detalle,
        )
        db.session.add(entrada)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error(
            "Error al insertar en bitacora_seguridad: %s motivo=%s", exc, motivo
        )


def _invalid_node_token_response(
    motivo: str,
    *,
    node_identifier: str = "",
    detalle: str | None = None,
):
    """Registra el rechazo y retorna la respuesta HTTP estandar."""
    _log_security_event(
        motivo=motivo,
        node_identifier=node_identifier,
        detalle=detalle,
    )
    return jsonify({"error": "token-nodo-invalido"}), 401


def node_token_required(fn: Callable) -> Callable:
    """Valida el token de autenticacion del nodo ESP32."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header: str | None = request.headers.get("Authorization")

        if not auth_header:
            return _invalid_node_token_response(
                "token-ausente",
                node_identifier=_get_node_identifier_from_body(),
                detalle="Cabecera Authorization ausente",
            )

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
            return _invalid_node_token_response(
                "token-malformado",
                node_identifier=_get_node_identifier_from_body(),
                detalle=f"Formato de cabecera invalido: {auth_header[:80]}",
            )

        raw_token = parts[1]
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        try:
            token_record: TokenNodo | None = (
                db.session.query(TokenNodo)
                .options(joinedload(TokenNodo.nodo))
                .filter_by(token_hash=token_hash)
                .first()
            )
        except SQLAlchemyError as exc:
            logger.error("Error al consultar token_nodo: %s", exc)
            return jsonify({"error": "token-nodo-invalido"}), 401

        if token_record is None:
            return _invalid_node_token_response(
                "token-no-encontrado",
                node_identifier=_get_node_identifier_from_body(),
                detalle="token_hash no encontrado en token_nodo",
            )

        if token_record.estado != "activo":
            return _invalid_node_token_response(
                "token-revocado",
                node_identifier=str(token_record.nodo_id),
                detalle=f"Token con estado '{token_record.estado}'",
            )

        nodo_autenticado = token_record.nodo
        if nodo_autenticado is None:
            return _invalid_node_token_response(
                "token-no-encontrado",
                node_identifier=_get_node_identifier_from_body(),
                detalle="Token activo sin nodo asociado",
            )

        node_id = _get_node_identifier_from_body()
        if node_id and nodo_autenticado.identificador != node_id:
            return _invalid_node_token_response(
                "token-nodo-no-coincide",
                node_identifier=node_id,
                detalle=(
                    "El token pertenece a un nodo distinto: "
                    f"{nodo_autenticado.identificador}"
                ),
            )

        g.nodo_token = token_record
        g.nodo_autenticado = nodo_autenticado
        return fn(*args, **kwargs)

    return wrapper
