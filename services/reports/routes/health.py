"""
Health check del Servicio_Reportes.

GET /reports/health
  - HTTP 200  {"status": "ok"}           cuando PostgreSQL responde
  - HTTP 503  {"error": "base-datos-no-disponible"}  cuando no hay conexión

Cumple: Requirements 9.3, 9.5
"""
from flask import Blueprint, jsonify
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from extensions import db

health_bp = Blueprint("health", __name__)


@health_bp.get("/reports/health")
def health():
    """Verifica la conectividad con PostgreSQL y retorna el estado del servicio."""
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ok"}), 200
    except (OperationalError, SQLAlchemyError):
        return jsonify({"error": "base-datos-no-disponible"}), 503
