"""Monitoreo de heartbeat y conectividad de nodos del Servicio_Acceso."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models.nodo_acceso import NodoAcceso
from sse.events import sse_channel

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def publish_node_status_event(node: NodoAcceso) -> None:
    """Publica un evento interno `node_status` al canal SSE."""
    try:
        sse_channel.publish(
            {
                "tipo": "node_status",
                "node_id": node.identificador,
                "estado": node.estado_conectividad,
            }
        )
    except Exception as exc:
        logger.error("Error al publicar evento node_status: %s", exc)


def mark_stale_nodes_offline(app) -> None:
    """Marca nodos con heartbeat vencido como `sin-conexion`."""
    with app.app_context():
        timeout_seconds = int(app.config.get("HEARTBEAT_TIMEOUT_S", 120))
        cutoff = _utcnow() - timedelta(seconds=timeout_seconds)

        try:
            stale_nodes = (
                db.session.query(NodoAcceso)
                .filter(
                    NodoAcceso.estado_conectividad != "sin-conexion",
                    NodoAcceso.ultimo_heartbeat.is_not(None),
                    NodoAcceso.ultimo_heartbeat < cutoff,
                )
                .all()
            )
        except SQLAlchemyError as exc:
            db.session.rollback()
            logger.error("Error al consultar nodos sin heartbeat: %s", exc)
            return

        if not stale_nodes:
            return

        now = _utcnow()
        changed_identifiers: list[str] = []
        for node in stale_nodes:
            node.estado_conectividad = "sin-conexion"
            node.updated_at = now
            changed_identifiers.append(node.identificador)

        try:
            db.session.commit()
        except SQLAlchemyError as exc:
            db.session.rollback()
            logger.error("Error al marcar nodos como sin-conexion: %s", exc)
            return

        for node in stale_nodes:
            publish_node_status_event(node)

        logger.info(
            "Nodos marcados como sin-conexion por timeout: %s",
            ", ".join(changed_identifiers),
        )


def configure_heartbeat_monitor(app) -> None:
    """Configura y arranca el scheduler del monitor de heartbeats."""
    if app.extensions.get("heartbeat_scheduler") is not None:
        return

    interval_seconds = int(app.config.get("HEARTBEAT_CHECK_INTERVAL_S", 30))
    scheduler = BackgroundScheduler(timezone="UTC", daemon=True)
    scheduler.add_job(
        func=lambda: mark_stale_nodes_offline(app),
        trigger="interval",
        seconds=interval_seconds,
        id="heartbeat-monitor",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    should_start = True
    if app.debug:
        should_start = os.environ.get("WERKZEUG_RUN_MAIN") == "true"

    if should_start:
        scheduler.start()
        logger.info(
            "Heartbeat monitor iniciado cada %ss con timeout %ss",
            interval_seconds,
            int(app.config.get("HEARTBEAT_TIMEOUT_S", 120)),
        )
    else:
        logger.info("Heartbeat monitor omitido en proceso reloader")

    app.extensions["heartbeat_scheduler"] = scheduler
