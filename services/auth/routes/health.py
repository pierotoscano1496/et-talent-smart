"""
Blueprint de health check para el Servicio_Autenticacion.

GET /auth/health
  - Retorna HTTP 200 {"status": "ok"} si la base de datos PostgreSQL responde.
  - Retorna HTTP 503 {"error": "base-datos-no-disponible"} si no responde.

Cumple: Requirements 9.3, 9.5
"""
from flask import Blueprint, jsonify
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from extensions import db

health_bp = Blueprint("health", __name__)


@health_bp.get("/auth/health")
def health_check():
    """
    Verifica la conectividad con PostgreSQL ejecutando SELECT 1.
    Retorna 200 si la BD responde, 503 en caso contrario.
    """
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ok"}), 200
    except (OperationalError, SQLAlchemyError):
        return jsonify({"error": "base-datos-no-disponible"}), 503
