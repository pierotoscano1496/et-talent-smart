"""
Health check del Servicio_Gestion.

GET /management/health
  - Retorna HTTP 200 {"status": "ok"} cuando PostgreSQL está accesible.
  - Retorna HTTP 503 {"error": "base-datos-no-disponible"} en caso contrario.

Requirements: 9.3, 9.5
"""
from flask import Blueprint, jsonify
from sqlalchemy import text
from extensions import db

health_bp = Blueprint("health", __name__)


@health_bp.get("/management/health")
def health():
    """Verifica que el servicio y la base de datos estén operativos."""
    try:
        # pool_pre_ping está activo, pero forzamos una consulta real para
        # confirmar que PostgreSQL responde (Req 9.5)
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ok"}), 200
    except Exception:
        return jsonify({"error": "base-datos-no-disponible"}), 503
