"""
Blueprint de reportes del Servicio_Reportes.

Endpoints:
  GET /reports/events             — listado paginado de eventos de acceso
  GET /reports/attendance-summary — resumen de asistencia por ambiente

Cumple: Requirements 6.1, 6.2, 6.4, 6.5, 6.6, 6.7, 9.3
"""
import math
import uuid
from datetime import date, datetime, timedelta, timezone

from authz import roles_required
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import case, func

from extensions import db
from models.ambiente import Ambiente
from models.estudiante import Estudiante
from models.evento_acceso import EventoAcceso
from models.nodo_acceso import NodoAcceso

reports_bp = Blueprint("reports", __name__)

# ---------------------------------------------------------------------------
# Helpers de validación
# ---------------------------------------------------------------------------

def _parse_date(value: str | None, param_name: str):
    """
    Parsea un string ISO 8601 (YYYY-MM-DD) a un objeto date.
    Retorna (date_obj, None) si OK, o (None, error_response) si inválido.
    """
    if not value:
        return None, (jsonify({"error": "parametros-invalidos"}), 400)
    try:
        return date.fromisoformat(value), None
    except ValueError:
        return None, (jsonify({"error": "parametros-invalidos"}), 400)


def _parse_uuid(value: str | None, param_name: str):
    """
    Parsea un string UUID. Retorna (uuid_obj, None) si OK, o None si el valor
    es None/vacío (campo opcional), o (None, error_response) si inválido.
    """
    if not value:
        return None, None
    try:
        return uuid.UUID(value), None
    except ValueError:
        return None, (jsonify({"error": "parametros-invalidos"}), 400)


def _parse_page_param(value: str | None, default: int, min_val: int, max_val: int | None):
    """
    Parsea un parámetro entero de paginación.
    Retorna (int_val, None) si OK, o (None, error_response) si inválido.
    """
    if not value:
        return default, None
    try:
        int_val = int(value)
    except (ValueError, TypeError):
        return None, (jsonify({"error": "parametros-invalidos"}), 400)

    if int_val < min_val:
        return None, (jsonify({"error": "parametros-invalidos"}), 400)
    if max_val is not None and int_val > max_val:
        return None, (jsonify({"error": "parametros-invalidos"}), 400)

    return int_val, None


# ---------------------------------------------------------------------------
# GET /reports/events
# ---------------------------------------------------------------------------

@reports_bp.get("/reports/events")
@roles_required("ADMINISTRADOR", "AUXILIAR_EDUCACION")
def get_events():
    """
    Listado paginado de eventos de acceso.

    Parámetros de query:
      fecha_inicio   (requerido, ISO 8601 date)
      fecha_fin      (requerido, ISO 8601 date)
      id_estudiante  (opcional, UUID)
      id_ambiente    (opcional, UUID)
      page           (opcional, entero ≥ 1, default 1)
      page_size      (opcional, 1-100, default 50)

    Respuestas:
      200  — datos paginados o lista vacía
      400  — parametros-invalidos | rango-maximo-excedido | resultado-excede-limite

    Cumple: Requirements 6.1, 6.4, 6.5, 6.6, 6.7
    """
    # -- Parsear fecha_inicio y fecha_fin (requeridos) ----------------------
    fecha_inicio_str = request.args.get("fecha_inicio")
    fecha_fin_str = request.args.get("fecha_fin")

    fecha_inicio, err = _parse_date(fecha_inicio_str, "fecha_inicio")
    if err:
        return err

    fecha_fin, err = _parse_date(fecha_fin_str, "fecha_fin")
    if err:
        return err

    # -- Validar rango máximo de 90 días ------------------------------------
    max_days: int = current_app.config.get("REPORT_MAX_DAYS", 90)
    if (fecha_fin - fecha_inicio).days > max_days:
        return jsonify({"error": "rango-maximo-excedido"}), 400

    # Verificar que fecha_fin no sea anterior a fecha_inicio
    if fecha_fin < fecha_inicio:
        return jsonify({"error": "parametros-invalidos"}), 400

    # -- Parsear filtros opcionales -----------------------------------------
    id_estudiante_str = request.args.get("id_estudiante")
    id_ambiente_str = request.args.get("id_ambiente")

    id_estudiante, err = _parse_uuid(id_estudiante_str, "id_estudiante")
    if err:
        return err

    id_ambiente, err = _parse_uuid(id_ambiente_str, "id_ambiente")
    if err:
        return err

    # -- Parsear paginación ------------------------------------------------
    page, err = _parse_page_param(request.args.get("page"), default=1, min_val=1, max_val=None)
    if err:
        return err

    page_size, err = _parse_page_param(
        request.args.get("page_size"), default=50, min_val=1, max_val=100
    )
    if err:
        return err

    # -- Construir query base ----------------------------------------------
    # Convertir fechas a timestamps UTC para la consulta:
    # fecha_inicio 00:00:00 UTC  →  fecha_fin 23:59:59.999999 UTC
    ts_inicio = datetime(
        fecha_inicio.year, fecha_inicio.month, fecha_inicio.day,
        0, 0, 0, tzinfo=timezone.utc
    )
    ts_fin = datetime(
        fecha_fin.year, fecha_fin.month, fecha_fin.day,
        23, 59, 59, 999999, tzinfo=timezone.utc
    )

    query = db.session.query(EventoAcceso).filter(
        EventoAcceso.timestamp_utc >= ts_inicio,
        EventoAcceso.timestamp_utc <= ts_fin,
    )

    if id_estudiante is not None:
        query = query.filter(EventoAcceso.estudiante_id == id_estudiante)

    if id_ambiente is not None:
        query = query.filter(EventoAcceso.ambiente_id == id_ambiente)

    # -- Contar registros antes de paginar ----------------------------------
    total: int = query.count()

    # Si total = 0 → responder con lista vacía
    if total == 0:
        return jsonify({"data": [], "total": 0}), 200

    # Si total > 10 000 → error
    max_rows: int = current_app.config.get("REPORT_MAX_ROWS", 10000)
    if total > max_rows:
        return jsonify({"error": "resultado-excede-limite"}), 400

    # -- Aplicar orden y paginación ----------------------------------------
    eventos = (
        query
        .order_by(EventoAcceso.timestamp_utc.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    total_pages = math.ceil(total / page_size)

    data = [e.to_report_dict() for e in eventos]

    return jsonify({
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": total_pages,
    }), 200


# ---------------------------------------------------------------------------
# GET /reports/attendance-summary
# ---------------------------------------------------------------------------

@reports_bp.get("/reports/attendance-summary")
@roles_required("ADMINISTRADOR", "AUXILIAR_EDUCACION")
def get_attendance_summary():
    """
    Resumen de asistencia por ambiente para un estudiante en un rango de fechas.

    Parámetros de query:
      id_estudiante  (requerido, UUID)
      fecha_inicio   (requerido, ISO 8601 date)
      fecha_fin      (requerido, ISO 8601 date)
    """
    fecha_inicio, err = _parse_date(request.args.get("fecha_inicio"), "fecha_inicio")
    if err:
        return err

    fecha_fin, err = _parse_date(request.args.get("fecha_fin"), "fecha_fin")
    if err:
        return err

    id_estudiante, err = _parse_uuid(
        request.args.get("id_estudiante"), "id_estudiante"
    )
    if err:
        return err
    if id_estudiante is None:
        return jsonify({"error": "parametros-invalidos"}), 400

    max_days: int = current_app.config.get("REPORT_MAX_DAYS", 90)
    if (fecha_fin - fecha_inicio).days > max_days:
        return jsonify({"error": "rango-maximo-excedido"}), 400

    if fecha_fin < fecha_inicio:
        return jsonify({"error": "parametros-invalidos"}), 400

    ts_inicio = datetime(
        fecha_inicio.year,
        fecha_inicio.month,
        fecha_inicio.day,
        0,
        0,
        0,
        tzinfo=timezone.utc,
    )
    ts_fin = datetime(
        fecha_fin.year,
        fecha_fin.month,
        fecha_fin.day,
        23,
        59,
        59,
        999999,
        tzinfo=timezone.utc,
    )

    authorized_count = func.sum(
        case((EventoAcceso.resultado == "autorizado", 1), else_=0)
    )
    denied_count = func.sum(
        case((EventoAcceso.resultado == "denegado", 1), else_=0)
    )

    query = (
        db.session.query(
            Ambiente.id.label("ambiente_id"),
            Ambiente.nombre.label("ambiente_nombre"),
            authorized_count.label("autorizados"),
            denied_count.label("denegados"),
            func.count(EventoAcceso.id).label("total"),
        )
        .join(Ambiente, Ambiente.id == EventoAcceso.ambiente_id)
        .filter(
            EventoAcceso.estudiante_id == id_estudiante,
            EventoAcceso.timestamp_utc >= ts_inicio,
            EventoAcceso.timestamp_utc <= ts_fin,
        )
        .group_by(Ambiente.id, Ambiente.nombre)
        .order_by(Ambiente.nombre.asc())
    )

    rows = query.all()

    if not rows:
        return jsonify(
            {
                "data": [],
                "total": 0,
                "id_estudiante": str(id_estudiante),
                "fecha_inicio": fecha_inicio.isoformat(),
                "fecha_fin": fecha_fin.isoformat(),
            }
        ), 200

    data = [
        {
            "ambiente": {
                "id": str(row.ambiente_id),
                "nombre": row.ambiente_nombre,
            },
            "autorizados": int(row.autorizados or 0),
            "denegados": int(row.denegados or 0),
            "total": int(row.total or 0),
        }
        for row in rows
    ]

    return jsonify(
        {
            "data": data,
            "total": len(data),
            "id_estudiante": str(id_estudiante),
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat(),
        }
    ), 200
