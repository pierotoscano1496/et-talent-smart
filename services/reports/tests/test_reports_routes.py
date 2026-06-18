"""Pruebas unitarias para rutas del Servicio_Reportes."""

from __future__ import annotations

import unittest
import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

from flask import Flask

from routes import reports as reports_routes


def _unwrap_response(response):
    """Normaliza respuestas Flask directas a (response, status_code)."""
    if isinstance(response, tuple):
        return response[0], response[1]
    return response, response.status_code


class ReportsRoutesTests(unittest.TestCase):
    """Cobertura base de endpoints implementados de reportes."""

    def setUp(self) -> None:
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.config["REPORT_MAX_DAYS"] = 90
        self.app.config["REPORT_MAX_ROWS"] = 10000

    def test_get_events_returns_empty_payload_when_no_matches(self):
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0

        mock_session = Mock()
        mock_session.query.return_value = mock_query

        with patch.object(reports_routes.db, "session", mock_session):
            with self.app.test_request_context(
                "/reports/events?fecha_inicio=2026-06-01&fecha_fin=2026-06-02"
            ):
                response = reports_routes.get_events.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        payload = flask_response.get_json()
        self.assertEqual(status_code, 200)
        self.assertEqual(payload, {"data": [], "total": 0})

    def test_get_events_rejects_results_over_limit(self):
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 10001

        mock_session = Mock()
        mock_session.query.return_value = mock_query

        with patch.object(reports_routes.db, "session", mock_session):
            with self.app.test_request_context(
                "/reports/events?fecha_inicio=2026-06-01&fecha_fin=2026-06-02"
            ):
                response = reports_routes.get_events.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        payload = flask_response.get_json()
        self.assertEqual(status_code, 400)
        self.assertEqual(payload["error"], "resultado-excede-limite")

    def test_get_events_returns_paginated_data(self):
        evento = Mock()
        evento.to_report_dict.return_value = {
            "evento_id": "evt-1",
            "ambiente_nombre": "Laboratorio A",
            "estudiante_nombre": "Ana Garcia",
            "resultado": "autorizado",
            "timestamp_utc": "2026-06-16T10:00:00+00:00",
        }

        ordered_query = Mock()
        ordered_query.offset.return_value.limit.return_value.all.return_value = [evento]

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = ordered_query

        mock_session = Mock()
        mock_session.query.return_value = mock_query

        with patch.object(reports_routes.db, "session", mock_session):
            with self.app.test_request_context(
                "/reports/events?fecha_inicio=2026-06-01&fecha_fin=2026-06-02&page=1&page_size=50"
            ):
                response = reports_routes.get_events.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        payload = flask_response.get_json()
        self.assertEqual(status_code, 200)
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["page_size"], 50)
        self.assertEqual(payload["pages"], 1)
        self.assertEqual(payload["data"][0]["evento_id"], "evt-1")

    def test_get_events_rejects_ranges_over_max_days(self):
        with self.app.test_request_context(
            "/reports/events?fecha_inicio=2026-01-01&fecha_fin=2026-05-01"
        ):
            response = reports_routes.get_events.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        payload = flask_response.get_json()
        self.assertEqual(status_code, 400)
        self.assertEqual(payload["error"], "rango-maximo-excedido")

    def test_get_attendance_summary_requires_student_id(self):
        with self.app.test_request_context(
            "/reports/attendance-summary?fecha_inicio=2026-06-01&fecha_fin=2026-06-02"
        ):
            response = reports_routes.get_attendance_summary.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        payload = flask_response.get_json()
        self.assertEqual(status_code, 400)
        self.assertEqual(payload["error"], "parametros-invalidos")

    def test_get_attendance_summary_groups_counts_by_ambiente(self):
        estudiante_id = uuid.uuid4()
        ambiente_a = uuid.uuid4()
        ambiente_b = uuid.uuid4()

        mock_query = Mock()
        (
            mock_query.join.return_value
            .filter.return_value
            .group_by.return_value
            .order_by.return_value
            .all.return_value
        ) = [
            SimpleNamespace(
                ambiente_id=ambiente_a,
                ambiente_nombre="Biblioteca",
                autorizados=3,
                denegados=1,
                total=4,
            ),
            SimpleNamespace(
                ambiente_id=ambiente_b,
                ambiente_nombre="Laboratorio A",
                autorizados=2,
                denegados=0,
                total=2,
            ),
        ]

        mock_session = Mock()
        mock_session.query.return_value = mock_query

        with patch.object(reports_routes.db, "session", mock_session):
            with self.app.test_request_context(
                "/reports/attendance-summary",
                query_string={
                    "id_estudiante": str(estudiante_id),
                    "fecha_inicio": date(2026, 6, 1).isoformat(),
                    "fecha_fin": date(2026, 6, 30).isoformat(),
                },
            ):
                response = reports_routes.get_attendance_summary.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        payload = flask_response.get_json()
        self.assertEqual(status_code, 200)
        self.assertEqual(payload["id_estudiante"], str(estudiante_id))
        self.assertEqual(payload["total"], 2)
        self.assertEqual(payload["data"][0]["ambiente"]["nombre"], "Biblioteca")
        self.assertEqual(payload["data"][0]["autorizados"], 3)
        self.assertEqual(payload["data"][0]["denegados"], 1)
        self.assertEqual(payload["data"][1]["total"], 2)

    def test_get_attendance_summary_returns_empty_when_no_matches(self):
        estudiante_id = uuid.uuid4()

        mock_query = Mock()
        (
            mock_query.join.return_value
            .filter.return_value
            .group_by.return_value
            .order_by.return_value
            .all.return_value
        ) = []

        mock_session = Mock()
        mock_session.query.return_value = mock_query

        with patch.object(reports_routes.db, "session", mock_session):
            with self.app.test_request_context(
                "/reports/attendance-summary",
                query_string={
                    "id_estudiante": str(estudiante_id),
                    "fecha_inicio": date(2026, 6, 1).isoformat(),
                    "fecha_fin": date(2026, 6, 30).isoformat(),
                },
            ):
                response = reports_routes.get_attendance_summary.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        payload = flask_response.get_json()
        self.assertEqual(status_code, 200)
        self.assertEqual(payload["data"], [])
        self.assertEqual(payload["total"], 0)
