"""Pruebas unitarias para rutas del Servicio_Acceso."""

from __future__ import annotations

import json
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from flask import Flask, g

from app import create_app
from extensions import db
from routes import access as access_routes


def _unwrap_response(response):
    """Normaliza respuestas Flask directas a (response, status_code)."""
    if isinstance(response, tuple):
        return response[0], response[1]
    return response, response.status_code


class AccessRoutesTests(unittest.TestCase):
    """Cobertura base de los endpoints implementados de acceso."""

    def setUp(self) -> None:
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True

    def test_post_heartbeat_marks_node_online_and_publishes_status(self):
        node = SimpleNamespace(
            identificador="NODE-01",
            estado_conectividad="sin-conexion",
            ultimo_heartbeat=None,
            updated_at=None,
        )
        mock_session = Mock()

        with patch.object(access_routes.db, "session", mock_session):
            with patch.object(
                access_routes, "publish_node_status_event"
            ) as publish_mock:
                with self.app.test_request_context("/access/heartbeat", method="POST"):
                    g.nodo_autenticado = node
                    response = access_routes.post_heartbeat.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        payload = flask_response.get_json()

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["node_id"], "NODE-01")
        self.assertEqual(payload["estado"], "en-linea")
        self.assertIsNotNone(payload["ultimo_heartbeat"])
        self.assertEqual(node.estado_conectividad, "en-linea")
        mock_session.commit.assert_called_once()
        publish_mock.assert_called_once_with(node)

    def test_post_event_authorized_returns_ok_and_publishes(self):
        estudiante_id = uuid.uuid4()
        nodo_id = uuid.uuid4()
        ambiente_id = uuid.uuid4()
        node = SimpleNamespace(
            id=nodo_id,
            identificador="NODE-01",
            estado="activo",
            ambiente_id=ambiente_id,
        )
        student = SimpleNamespace(
            id=estudiante_id,
            nombre_completo="Ana Garcia",
            estado="activo",
        )
        tag = SimpleNamespace(estudiante=student)

        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = tag

        with patch.object(access_routes.db, "session", mock_session):
            with patch.object(
                access_routes, "_publish_sse_event"
            ) as publish_mock:
                with self.app.test_request_context(
                    "/access/events",
                    method="POST",
                    json={
                        "tag_rfid": "A1B2C3D4",
                        "node_id": "NODE-01",
                        "timestamp_utc": "2026-06-16T10:00:00Z",
                    },
                ):
                    g.nodo_autenticado = node
                    response = access_routes.post_event.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        payload = flask_response.get_json()
        self.assertEqual(status_code, 200)
        self.assertEqual(payload["resultado"], "autorizado")
        self.assertIsNone(payload["codigo_resultado"])
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        publish_mock.assert_called_once()

    def test_post_event_unknown_tag_returns_denied(self):
        nodo_id = uuid.uuid4()
        ambiente_id = uuid.uuid4()
        node = SimpleNamespace(
            id=nodo_id,
            identificador="NODE-01",
            estado="activo",
            ambiente_id=ambiente_id,
        )

        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with patch.object(access_routes.db, "session", mock_session):
            with patch.object(
                access_routes, "_publish_sse_event"
            ) as publish_mock:
                with self.app.test_request_context(
                    "/access/events",
                    method="POST",
                    json={
                        "tag_rfid": "A1B2C3D4",
                        "node_id": "NODE-01",
                        "timestamp_utc": "2026-06-16T10:00:00Z",
                    },
                ):
                    g.nodo_autenticado = node
                    response = access_routes.post_event.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        payload = flask_response.get_json()
        self.assertEqual(status_code, 200)
        self.assertEqual(payload["resultado"], "denegado")
        self.assertEqual(payload["codigo_resultado"], "tag-no-registrado")
        publish_mock.assert_called_once()

    def test_post_event_inactive_student_returns_denied(self):
        estudiante_id = uuid.uuid4()
        nodo_id = uuid.uuid4()
        ambiente_id = uuid.uuid4()
        node = SimpleNamespace(
            id=nodo_id,
            identificador="NODE-01",
            estado="activo",
            ambiente_id=ambiente_id,
        )
        student = SimpleNamespace(
            id=estudiante_id,
            nombre_completo="Ana Garcia",
            estado="inactivo",
        )
        tag = SimpleNamespace(estudiante=student)

        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = tag

        with patch.object(access_routes.db, "session", mock_session):
            with patch.object(
                access_routes, "_publish_sse_event"
            ) as publish_mock:
                with self.app.test_request_context(
                    "/access/events",
                    method="POST",
                    json={
                        "tag_rfid": "A1B2C3D4",
                        "node_id": "NODE-01",
                        "timestamp_utc": "2026-06-16T10:00:00Z",
                    },
                ):
                    g.nodo_autenticado = node
                    response = access_routes.post_event.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        payload = flask_response.get_json()
        self.assertEqual(status_code, 200)
        self.assertEqual(payload["resultado"], "denegado")
        self.assertEqual(payload["codigo_resultado"], "estudiante-inactivo")
        publish_mock.assert_called_once()

    def test_post_event_inactive_node_returns_denied_without_tag_lookup(self):
        nodo_id = uuid.uuid4()
        ambiente_id = uuid.uuid4()
        node = SimpleNamespace(
            id=nodo_id,
            identificador="NODE-01",
            estado="inactivo",
            ambiente_id=ambiente_id,
        )

        mock_session = Mock()

        with patch.object(access_routes.db, "session", mock_session):
            with patch.object(
                access_routes, "_publish_sse_event"
            ) as publish_mock:
                with self.app.test_request_context(
                    "/access/events",
                    method="POST",
                    json={
                        "tag_rfid": "A1B2C3D4",
                        "node_id": "NODE-01",
                        "timestamp_utc": "2026-06-16T10:00:00Z",
                    },
                ):
                    g.nodo_autenticado = node
                    response = access_routes.post_event.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        payload = flask_response.get_json()
        self.assertEqual(status_code, 200)
        self.assertEqual(payload["codigo_resultado"], "nodo-inactivo")
        mock_session.query.assert_not_called()
        publish_mock.assert_called_once()

    def test_get_events_returns_paginated_enriched_data(self):
        ts = datetime(2026, 6, 16, 10, 0, 0, tzinfo=timezone.utc)
        event_id = uuid.uuid4()
        node_id = uuid.uuid4()
        ambiente_id = uuid.uuid4()
        estudiante_id = uuid.uuid4()

        total_result = Mock()
        total_result.scalar_one.return_value = 1

        mappings_result = Mock()
        mappings_result.all.return_value = [
            {
                "id": event_id,
                "tag_rfid": "A1B2C3D4",
                "timestamp_utc": ts,
                "resultado": "autorizado",
                "codigo_resultado": None,
                "origen": "nodo",
                "nodo_id": node_id,
                "nodo_identificador": "NODE-01",
                "nodo_estado": "activo",
                "ambiente_id": ambiente_id,
                "ambiente_nombre": "Laboratorio A",
                "estudiante_id": estudiante_id,
                "estudiante_nombre": "Ana Garcia",
                "estudiante_codigo": "STU001",
            }
        ]

        rows_result = Mock()
        rows_result.mappings.return_value = mappings_result

        mock_session = Mock()
        mock_session.execute.side_effect = [total_result, rows_result]

        with patch.object(access_routes.db, "session", mock_session):
            with self.app.test_request_context("/access/events?page=1&page_size=10"):
                response = access_routes.get_events.__wrapped__()

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["page_size"], 10)
        self.assertEqual(payload["data"][0]["tag_rfid"], "A1B2C3D4")
        self.assertEqual(payload["data"][0]["nodo"]["identificador"], "NODE-01")
        self.assertEqual(payload["data"][0]["ambiente"]["nombre"], "Laboratorio A")
        self.assertEqual(
            payload["data"][0]["estudiante"]["nombre_completo"], "Ana Garcia"
        )

    def test_get_nodes_status_returns_current_connectivity(self):
        ts = datetime(2026, 6, 16, 10, 5, 0, tzinfo=timezone.utc)
        node_id = uuid.uuid4()
        ambiente_id = uuid.uuid4()

        mappings_result = Mock()
        mappings_result.all.return_value = [
            {
                "id": node_id,
                "identificador": "NODE-01",
                "descripcion": "Puerta principal",
                "estado": "activo",
                "estado_conectividad": "en-linea",
                "ultimo_heartbeat": ts,
                "updated_at": ts,
                "ambiente_id": ambiente_id,
                "ambiente_nombre": "Laboratorio A",
            }
        ]
        rows_result = Mock()
        rows_result.mappings.return_value = mappings_result

        mock_session = Mock()
        mock_session.execute.return_value = rows_result

        with patch.object(access_routes.db, "session", mock_session):
            with self.app.test_request_context("/access/nodes/status"):
                response = access_routes.get_nodes_status.__wrapped__()

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["data"][0]["identificador"], "NODE-01")
        self.assertEqual(payload["data"][0]["estado_conectividad"], "en-linea")
        self.assertEqual(payload["data"][0]["ambiente"]["nombre"], "Laboratorio A")

    def test_get_events_stream_formats_access_and_keep_alive_messages(self):
        stream_payloads = iter(
            [
                {
                    "evento_id": "evt-1",
                    "estudiante": "Ana Garcia",
                    "ambiente": "Laboratorio A",
                    "timestamp": "2026-06-16T10:00:00+00:00",
                    "resultado": "autorizado",
                },
                {},
                {
                    "tipo": "node_status",
                    "node_id": "NODE-01",
                    "estado": "sin-conexion",
                },
            ]
        )

        with patch.object(
            access_routes.sse_channel,
            "subscribe",
            return_value=stream_payloads,
        ):
            with self.app.test_request_context("/access/events/stream"):
                response = access_routes.get_events_stream.__wrapped__()
                iterator = iter(response.response)
                first_chunk = next(iterator)
                second_chunk = next(iterator)
                third_chunk = next(iterator)

        self.assertEqual(response.mimetype, "text/event-stream")
        self.assertEqual(response.headers["Cache-Control"], "no-cache")
        self.assertIn('"evento_id": "evt-1"', first_chunk)
        self.assertEqual(second_chunk, ": keep-alive\n\n")
        self.assertIn('"tipo": "node_status"', third_chunk)
        self.assertEqual(
            json.loads(first_chunk.removeprefix("data: ").strip())["resultado"],
            "autorizado",
        )


class TestAccessModelRegistry(unittest.TestCase):
    """Previene regresiones de registro de modelos requeridos por SQLAlchemy."""

    def test_create_app_registers_ambiente_table(self):
        app = create_app()

        with app.app_context():
            self.assertIn("ambiente", db.metadata.tables)
