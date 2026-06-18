"""Pruebas unitarias para rutas del Servicio_Gestion."""

from __future__ import annotations

import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import Mock, patch

from flask import Flask

from routes import management as management_routes


def _unwrap_response(response):
    """Normaliza respuestas Flask directas a (response, status_code)."""
    if isinstance(response, tuple):
        return response[0], response[1]
    return response, response.status_code


class ManagementRoutesTests(unittest.TestCase):
    """Cobertura base de los endpoints implementados de management."""

    def setUp(self) -> None:
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self) -> None:
        self.app_context.pop()

    def test_create_student_success(self):
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with patch.object(management_routes.db, "session", mock_session):
            with patch.object(
                management_routes,
                "_student_payload",
                return_value={"codigo": "STU001", "tag_rfid": None},
            ):
                with self.app.test_request_context(
                    "/management/students",
                    method="POST",
                    json={
                        "nombre_completo": "Ana Garcia",
                        "codigo": "STU001",
                        "grado_seccion": "3A",
                    },
                ):
                    response = management_routes.create_student.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        payload = flask_response.get_json()
        self.assertEqual(status_code, 201)
        self.assertEqual(payload["codigo"], "STU001")
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_create_student_duplicate_code_returns_409(self):
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = object()

        with patch.object(management_routes.db, "session", mock_session):
            with self.app.test_request_context(
                "/management/students",
                method="POST",
                json={
                    "nombre_completo": "Ana Garcia",
                    "codigo": "STU001",
                    "grado_seccion": "3A",
                },
            ):
                response = management_routes.create_student.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        self.assertEqual(status_code, 409)
        self.assertEqual(flask_response.get_json()["error"], "codigo-duplicado")

    def test_update_student_partial_preserves_payload(self):
        student_id = uuid.uuid4()
        student = SimpleNamespace(
            nombre_completo="Ana Garcia",
            grado_seccion="3A",
            estado="activo",
            updated_at=None,
        )

        fake_estudiante_model = SimpleNamespace(query=SimpleNamespace(get=Mock(return_value=student)))
        with patch.object(management_routes, "Estudiante", fake_estudiante_model):
            with patch.object(management_routes, "_student_payload", return_value={"ok": True}):
                with patch.object(management_routes.db, "session", Mock()):
                    with self.app.test_request_context(
                        f"/management/students/{student_id}",
                        method="PATCH",
                        json={"grado_seccion": "4B", "estado": "inactivo"},
                    ):
                        response = management_routes.update_student.__wrapped__(str(student_id))

        flask_response, status_code = _unwrap_response(response)
        self.assertEqual(status_code, 200)
        self.assertEqual(flask_response.get_json()["ok"], True)
        self.assertEqual(student.grado_seccion, "4B")
        self.assertEqual(student.estado, "inactivo")

    def test_assign_rfid_conflict_returns_409(self):
        student_id = uuid.uuid4()
        student = SimpleNamespace(id=student_id, tag_activo=None)
        existing_tag = SimpleNamespace(estudiante_id=uuid.uuid4())

        fake_estudiante_model = SimpleNamespace(query=SimpleNamespace(get=Mock(return_value=student)))
        fake_tag_model = SimpleNamespace(
            query=SimpleNamespace(
                filter_by=Mock(
                    return_value=SimpleNamespace(first=Mock(return_value=existing_tag))
                )
            )
        )
        with patch.object(management_routes, "Estudiante", fake_estudiante_model):
            with patch.object(management_routes, "TagRFID", fake_tag_model):
                with self.app.test_request_context(
                    f"/management/students/{student_id}/rfid",
                    method="POST",
                    json={"uid_hex": "A1B2C3D4"},
                ):
                    response = management_routes.assign_rfid.__wrapped__(str(student_id))

        flask_response, status_code = _unwrap_response(response)
        self.assertEqual(status_code, 409)
        self.assertEqual(flask_response.get_json()["error"], "tag-en-uso")

    def test_create_environment_success(self):
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with patch.object(management_routes.db, "session", mock_session):
            with patch.object(
                management_routes,
                "_environment_payload",
                return_value={"nombre": "Laboratorio A"},
            ):
                with self.app.test_request_context(
                    "/management/environments",
                    method="POST",
                    json={"nombre": "Laboratorio A", "ubicacion": "Pabellon 1"},
                ):
                    response = management_routes.create_environment.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        self.assertEqual(status_code, 201)
        self.assertEqual(flask_response.get_json()["nombre"], "Laboratorio A")

    def test_create_environment_duplicate_returns_409(self):
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = object()

        with patch.object(management_routes.db, "session", mock_session):
            with self.app.test_request_context(
                "/management/environments",
                method="POST",
                json={"nombre": "Laboratorio A"},
            ):
                response = management_routes.create_environment.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        self.assertEqual(status_code, 409)
        self.assertEqual(
            flask_response.get_json()["error"], "nombre-ambiente-duplicado"
        )

    def test_create_node_missing_environment_returns_422(self):
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        ambiente_id = uuid.uuid4()

        with patch.object(management_routes.db, "session", mock_session):
            with patch.object(
                management_routes.Ambiente,
                "query",
                SimpleNamespace(get=Mock(return_value=None)),
            ):
                with self.app.test_request_context(
                    "/management/nodes",
                    method="POST",
                    json={
                        "identificador": "NODO-LAB-01",
                        "id_ambiente": str(ambiente_id),
                    },
                ):
                    response = management_routes.create_node.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        self.assertEqual(status_code, 422)
        self.assertEqual(flask_response.get_json()["error"], "ambiente-no-encontrado")

    def test_manage_node_token_generate_returns_plain_token(self):
        node_id = uuid.uuid4()
        node = SimpleNamespace(id=node_id)
        mock_session = Mock()

        fake_node_model = SimpleNamespace(query=SimpleNamespace(get=Mock(return_value=node)))
        fake_token_model = SimpleNamespace(
            query=SimpleNamespace(
                filter_by=Mock(
                    return_value=SimpleNamespace(all=Mock(return_value=[]))
                )
            )
        )
        with patch.object(management_routes, "NodoAcceso", fake_node_model):
            with patch.object(management_routes, "TokenNodo", fake_token_model):
                with patch.object(management_routes.db, "session", mock_session):
                    with patch.object(
                        management_routes.secrets,
                        "token_urlsafe",
                        return_value="plain-node-token",
                    ):
                        with self.app.test_request_context(
                            f"/management/nodes/{node_id}/token",
                            method="POST",
                            json={"action": "generate"},
                        ):
                            response = management_routes.manage_node_token.__wrapped__(
                                str(node_id)
                            )

        flask_response, status_code = _unwrap_response(response)
        payload = flask_response.get_json()
        self.assertEqual(status_code, 200)
        self.assertEqual(payload["accion"], "generate")
        self.assertEqual(payload["estado_token"], "activo")
        self.assertEqual(payload["token"], "plain-node-token")
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_create_user_success(self):
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with patch.object(management_routes.db, "session", mock_session):
            with patch.object(
                management_routes, "hash_password", return_value="hashed-password"
            ):
                with patch.object(
                    management_routes,
                    "_user_payload",
                    return_value={"email": "admin@escuela.pe", "rol": "ADMINISTRADOR"},
                ):
                    with self.app.test_request_context(
                        "/management/users",
                        method="POST",
                        json={
                            "nombre_completo": "Admin Principal",
                            "email": "admin@escuela.pe",
                            "password_temporal": "Temporal123",
                            "rol": "ADMINISTRADOR",
                        },
                    ):
                        response = management_routes.create_user.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        self.assertEqual(status_code, 201)
        self.assertEqual(flask_response.get_json()["email"], "admin@escuela.pe")
        mock_session.commit.assert_called_once()

    def test_create_user_duplicate_email_returns_409(self):
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = object()

        with patch.object(management_routes.db, "session", mock_session):
            with self.app.test_request_context(
                "/management/users",
                method="POST",
                json={
                    "nombre_completo": "Admin Principal",
                    "email": "admin@escuela.pe",
                    "password_temporal": "Temporal123",
                    "rol": "ADMINISTRADOR",
                },
            ):
                response = management_routes.create_user.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        self.assertEqual(status_code, 409)
        self.assertEqual(flask_response.get_json()["error"], "email-duplicado")

    def test_update_user_deactivation(self):
        user_id = uuid.uuid4()
        user = SimpleNamespace(rol="ADMINISTRADOR", estado="activo", updated_at=None)

        fake_user_model = SimpleNamespace(query=SimpleNamespace(get=Mock(return_value=user)))
        with patch.object(management_routes, "UsuarioWeb", fake_user_model):
            with patch.object(
                management_routes, "_user_payload", return_value={"estado": "inactivo"}
            ):
                with patch.object(management_routes.db, "session", Mock()):
                    with self.app.test_request_context(
                        f"/management/users/{user_id}",
                        method="PATCH",
                        json={"estado": "inactivo"},
                    ):
                        response = management_routes.update_user.__wrapped__(str(user_id))

        flask_response, status_code = _unwrap_response(response)
        self.assertEqual(status_code, 200)
        self.assertEqual(flask_response.get_json()["estado"], "inactivo")
        self.assertEqual(user.estado, "inactivo")
