"""Blueprint del Servicio_Acceso."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from flask import Blueprint, Response, g, jsonify, request, stream_with_context
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from auth.node_token import node_token_required
from auth.web_roles import roles_required
from extensions import db
from heartbeat import publish_node_status_event
from models.evento_acceso import EventoAcceso
from models.nodo_acceso import NodoAcceso
from models.tag_rfid import TagRFID
from sse.events import sse_channel

logger = logging.getLogger(__name__)

access_bp = Blueprint("access", __name__)

_TAG_RFID_RE = re.compile(r"^[0-9A-Fa-f]{8}$")


def _parse_iso8601(value: str) -> datetime | None:
    """Parsea un timestamp ISO 8601 con timezone."""
    if not isinstance(value, str):
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


def _pagination_params() -> tuple[int, int]:
    """Obtiene `page` y `page_size` con limites seguros."""
    try:
        page = max(int(request.args.get("page", 1)), 1)
        page_size = int(request.args.get("page_size", 50))
    except (TypeError, ValueError):
        return 1, 50

    return page, min(max(page_size, 1), 100)


@access_bp.post("/access/events")
@node_token_required
def post_event():
    """
    Procesa un evento RFID proveniente del ESP32.

    Flujo:
      1. Validar body JSON: tag_rfid, node_id, timestamp_utc
      2. Verificar que el token pertenezca al node_id reportado
      3. Si el nodo esta inactivo, persistir denegado/nodo-inactivo
      4. Si el nodo esta activo, resolver tag y estudiante
      5. Persistir EventoAcceso
      6. Publicar evento al canal SSE interno
      7. Retornar HTTP 200 con resultado y evento_id
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "datos-invalidos"}), 400

    tag_rfid_raw = data.get("tag_rfid")
    node_id_raw = data.get("node_id")
    timestamp_raw = data.get("timestamp_utc")

    if not tag_rfid_raw or not _TAG_RFID_RE.match(str(tag_rfid_raw)):
        return jsonify({"error": "datos-invalidos"}), 400

    if not node_id_raw or not isinstance(node_id_raw, str) or not node_id_raw.strip():
        return jsonify({"error": "datos-invalidos"}), 400

    if not timestamp_raw:
        return jsonify({"error": "datos-invalidos"}), 400
    timestamp_utc = _parse_iso8601(str(timestamp_raw))
    if timestamp_utc is None:
        return jsonify({"error": "datos-invalidos"}), 400

    tag_rfid_upper = str(tag_rfid_raw).upper()
    node_id_str = str(node_id_raw).strip()

    nodo: NodoAcceso | None = getattr(g, "nodo_autenticado", None)
    if nodo is None:
        logger.error("node_token_required no inyecto g.nodo_autenticado")
        return jsonify({"error": "token-nodo-invalido"}), 401

    if nodo.identificador != node_id_str:
        return jsonify({"error": "token-nodo-invalido"}), 401

    if nodo.estado == "inactivo":
        evento = EventoAcceso(
            tag_rfid=tag_rfid_upper,
            nodo_id=nodo.id,
            ambiente_id=nodo.ambiente_id,
            estudiante_id=None,
            timestamp_utc=timestamp_utc,
            resultado="denegado",
            codigo_resultado="nodo-inactivo",
        )
        try:
            db.session.add(evento)
            db.session.commit()
        except SQLAlchemyError as exc:
            db.session.rollback()
            logger.error("Error al persistir evento (nodo inactivo): %s", exc)
            return jsonify({"error": "error-interno"}), 500

        _publish_sse_event(evento, nodo, estudiante_nombre=None)
        return jsonify(
            {
                "resultado": "denegado",
                "codigo_resultado": "nodo-inactivo",
                "evento_id": str(evento.id),
            }
        ), 200

    try:
        tag: TagRFID | None = (
            db.session.query(TagRFID)
            .filter(
                TagRFID.uid_hex == tag_rfid_upper,
                TagRFID.activo.is_(True),
            )
            .first()
        )
    except SQLAlchemyError as exc:
        logger.error("Error al consultar tag_rfid: %s", exc)
        return jsonify({"error": "error-interno"}), 500

    if tag is None:
        resultado = "denegado"
        codigo_resultado = "tag-no-registrado"
        estudiante_id = None
        estudiante_nombre = None
    else:
        estudiante = tag.estudiante
        estudiante_id = estudiante.id
        estudiante_nombre = estudiante.nombre_completo
        if estudiante.estado == "activo":
            resultado = "autorizado"
            codigo_resultado = None
        else:
            resultado = "denegado"
            codigo_resultado = "estudiante-inactivo"

    evento = EventoAcceso(
        tag_rfid=tag_rfid_upper,
        nodo_id=nodo.id,
        ambiente_id=nodo.ambiente_id,
        estudiante_id=estudiante_id,
        timestamp_utc=timestamp_utc,
        resultado=resultado,
        codigo_resultado=codigo_resultado,
    )
    try:
        db.session.add(evento)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("Error al persistir EventoAcceso: %s", exc)
        return jsonify({"error": "error-interno"}), 500

    _publish_sse_event(evento, nodo, estudiante_nombre=estudiante_nombre)

    return jsonify(
        {
            "resultado": resultado,
            "codigo_resultado": codigo_resultado,
            "evento_id": str(evento.id),
        }
    ), 200


def _get_ambiente_nombre(ambiente_id) -> str | None:
    """Obtiene el nombre del ambiente por su ID."""
    try:
        row = db.session.execute(
            text("SELECT nombre FROM ambiente WHERE id = :id"),
            {"id": str(ambiente_id)},
        ).fetchone()
        return row[0] if row else None
    except Exception:
        return None


def _publish_sse_event(
    evento: EventoAcceso,
    nodo: NodoAcceso,
    estudiante_nombre: str | None,
) -> None:
    """Publica un evento de acceso al canal SSE interno."""
    try:
        ambiente_nombre = _get_ambiente_nombre(nodo.ambiente_id)
        payload = {
            "evento_id": str(evento.id),
            "estudiante": estudiante_nombre,
            "ambiente": ambiente_nombre,
            "timestamp": evento.timestamp_utc.isoformat(),
            "resultado": evento.resultado,
            "codigo_resultado": evento.codigo_resultado,
        }
        sse_channel.publish(payload)
    except Exception as exc:
        logger.error("Error al publicar evento SSE: %s", exc)


def _sse_stream():
    """Convierte el canal interno a un stream SSE HTTP."""
    for payload in sse_channel.subscribe():
        if not payload:
            yield ": keep-alive\n\n"
            continue

        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@access_bp.post("/access/heartbeat")
@node_token_required
def post_heartbeat():
    """Recibe el heartbeat del nodo y actualiza su conectividad."""
    nodo: NodoAcceso | None = getattr(g, "nodo_autenticado", None)
    if nodo is None:
        logger.error("node_token_required no inyecto g.nodo_autenticado en heartbeat")
        return jsonify({"error": "token-nodo-invalido"}), 401

    now = datetime.now(timezone.utc)
    was_online = nodo.estado_conectividad == "en-linea"

    nodo.ultimo_heartbeat = now
    nodo.estado_conectividad = "en-linea"
    nodo.updated_at = now

    try:
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("Error al actualizar heartbeat de nodo %s: %s", nodo.identificador, exc)
        return jsonify({"error": "error-interno"}), 500

    if not was_online:
        publish_node_status_event(nodo)

    return jsonify(
        {
            "node_id": nodo.identificador,
            "estado": nodo.estado_conectividad,
            "ultimo_heartbeat": nodo.ultimo_heartbeat.isoformat(),
        }
    ), 200


@access_bp.get("/access/events")
@roles_required("ADMINISTRADOR", "AUXILIAR_EDUCACION")
def get_events():
    """Retorna el listado paginado de eventos de acceso."""
    page, page_size = _pagination_params()
    offset = (page - 1) * page_size

    total_query = text("SELECT COUNT(*) FROM evento_acceso")
    events_query = text(
        """
        SELECT
            e.id,
            e.tag_rfid,
            e.timestamp_utc,
            e.resultado,
            e.codigo_resultado,
            e.origen,
            n.id AS nodo_id,
            n.identificador AS nodo_identificador,
            n.estado AS nodo_estado,
            a.id AS ambiente_id,
            a.nombre AS ambiente_nombre,
            s.id AS estudiante_id,
            s.nombre_completo AS estudiante_nombre,
            s.codigo AS estudiante_codigo
        FROM evento_acceso e
        JOIN nodo_acceso n ON n.id = e.nodo_id
        JOIN ambiente a ON a.id = e.ambiente_id
        LEFT JOIN estudiante s ON s.id = e.estudiante_id
        ORDER BY e.timestamp_utc DESC
        LIMIT :limit OFFSET :offset
        """
    )

    try:
        total = db.session.execute(total_query).scalar_one()
        rows = db.session.execute(
            events_query,
            {"limit": page_size, "offset": offset},
        ).mappings().all()
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("Error al listar eventos de acceso: %s", exc)
        return jsonify({"error": "error-interno"}), 500

    data = [
        {
            "id": str(row["id"]),
            "tag_rfid": row["tag_rfid"],
            "timestamp_utc": row["timestamp_utc"].isoformat()
            if row["timestamp_utc"]
            else None,
            "resultado": row["resultado"],
            "codigo_resultado": row["codigo_resultado"],
            "origen": row["origen"],
            "nodo": {
                "id": str(row["nodo_id"]),
                "identificador": row["nodo_identificador"],
                "estado": row["nodo_estado"],
            },
            "ambiente": {
                "id": str(row["ambiente_id"]),
                "nombre": row["ambiente_nombre"],
            },
            "estudiante": (
                {
                    "id": str(row["estudiante_id"]),
                    "nombre_completo": row["estudiante_nombre"],
                    "codigo": row["estudiante_codigo"],
                }
                if row["estudiante_id"] is not None
                else None
            ),
        }
        for row in rows
    ]

    return jsonify(
        {
            "data": data,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@access_bp.get("/access/nodes/status")
@roles_required("ADMINISTRADOR", "AUXILIAR_EDUCACION")
def get_nodes_status():
    """Retorna el estado actual de conectividad de los nodos."""
    query = text(
        """
        SELECT
            n.id,
            n.identificador,
            n.descripcion,
            n.estado,
            n.estado_conectividad,
            n.ultimo_heartbeat,
            n.updated_at,
            a.id AS ambiente_id,
            a.nombre AS ambiente_nombre
        FROM nodo_acceso n
        JOIN ambiente a ON a.id = n.ambiente_id
        ORDER BY n.identificador ASC
        """
    )

    try:
        rows = db.session.execute(query).mappings().all()
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("Error al consultar estado de nodos: %s", exc)
        return jsonify({"error": "error-interno"}), 500

    data = [
        {
            "id": str(row["id"]),
            "identificador": row["identificador"],
            "descripcion": row["descripcion"],
            "estado": row["estado"],
            "estado_conectividad": row["estado_conectividad"],
            "ultimo_heartbeat": row["ultimo_heartbeat"].isoformat()
            if row["ultimo_heartbeat"]
            else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            "ambiente": {
                "id": str(row["ambiente_id"]),
                "nombre": row["ambiente_nombre"],
            },
        }
        for row in rows
    ]

    return jsonify({"data": data, "total": len(data)})


@access_bp.get("/access/events/stream")
@roles_required("ADMINISTRADOR", "AUXILIAR_EDUCACION")
def get_events_stream():
    """Stream Server-Sent Events de eventos de acceso y estado de nodos."""
    response = Response(
        stream_with_context(_sse_stream()),
        mimetype="text/event-stream",
    )
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response
