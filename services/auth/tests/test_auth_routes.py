"""Pruebas unitarias para rutas del Servicio_Autenticacion."""

from __future__ import annotations

import uuid
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from flask import Flask
from sqlalchemy.exc import IntegrityError

from app import create_app
from routes import auth as auth_routes


def _unwrap_response(response):
    """Normaliza respuestas Flask directas a (response, status_code)."""
    if isinstance(response, tuple):
        return response[0], response[1]
    return response, response.status_code


class AuthRoutesTests(unittest.TestCase):
    """Cobertura base de login, logout y cambio de contrasena."""

    def setUp(self) -> None:
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self) -> None:
        self.app_context.pop()

    def test_login_success_returns_token_payload(self):
        user = SimpleNamespace(
            id=uuid.uuid4(),
            rol="ADMINISTRADOR",
            nombre_completo="Admin Principal",
            primer_login=True,
            estado="activo",
            password_hash="hash",
            to_login_dict=lambda token: {
                "token": token,
                "rol": "ADMINISTRADOR",
                "nombre": "Admin Principal",
                "primer_login": True,
            },
        )

        with patch.object(auth_routes, "_find_user_by_email", return_value=user):
            with patch.object(auth_routes, "verify_password", return_value=True):
                with patch.object(
                    auth_routes,
                    "create_access_token",
                    return_value="jwt-token-value",
                ) as create_token:
                    with self.app.test_request_context(
                        "/auth/login",
                        method="POST",
                        json={
                            "email": "ADMIN@escuela.pe",
                            "password": "Temporal123",
                        },
                    ):
                        response = auth_routes.login()

        flask_response, status_code = _unwrap_response(response)
        payload = flask_response.get_json()
        self.assertEqual(status_code, 200)
        self.assertEqual(payload["token"], "jwt-token-value")
        self.assertEqual(payload["rol"], "ADMINISTRADOR")
        create_token.assert_called_once()

    def test_login_invalid_payload_returns_400(self):
        with self.app.test_request_context(
            "/auth/login",
            method="POST",
            json={"email": "admin@escuela.pe"},
        ):
            response = auth_routes.login()

        flask_response, status_code = _unwrap_response(response)
        self.assertEqual(status_code, 400)
        self.assertEqual(flask_response.get_json()["error"], "datos-invalidos")

    def test_login_rejects_inactive_user(self):
        user = SimpleNamespace(
            estado="inactivo",
            password_hash="hash",
        )

        with patch.object(auth_routes, "_find_user_by_email", return_value=user):
            with self.app.test_request_context(
                "/auth/login",
                method="POST",
                json={"email": "admin@escuela.pe", "password": "Temporal123"},
            ):
                response = auth_routes.login()

        flask_response, status_code = _unwrap_response(response)
        self.assertEqual(status_code, 401)
        self.assertEqual(
            flask_response.get_json()["error"], "credenciales-invalidas"
        )

    def test_login_rejects_invalid_password(self):
        user = SimpleNamespace(
            estado="activo",
            password_hash="hash",
        )

        with patch.object(auth_routes, "_find_user_by_email", return_value=user):
            with patch.object(auth_routes, "verify_password", return_value=False):
                with self.app.test_request_context(
                    "/auth/login",
                    method="POST",
                    json={"email": "admin@escuela.pe", "password": "incorrecta"},
                ):
                    response = auth_routes.login()

        flask_response, status_code = _unwrap_response(response)
        self.assertEqual(status_code, 401)
        self.assertEqual(
            flask_response.get_json()["error"], "credenciales-invalidas"
        )

    def test_logout_success_revokes_current_token(self):
        user_id = uuid.uuid4()
        mock_session = Mock()

        with patch.object(
            auth_routes,
            "get_jwt",
            return_value={"jti": "token-jti", "exp": 1_900_000_000},
        ):
            with patch.object(
                auth_routes, "get_jwt_identity", return_value=str(user_id)
            ):
                with patch.object(auth_routes.db, "session", mock_session):
                    with self.app.test_request_context("/auth/logout", method="POST"):
                        response = auth_routes.logout.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        self.assertEqual(status_code, 200)
        self.assertEqual(flask_response.get_json()["mensaje"], "sesion-cerrada")
        mock_session.add.assert_called_once()
        revoked_token = mock_session.add.call_args.args[0]
        self.assertEqual(revoked_token.jti, "token-jti")
        self.assertEqual(revoked_token.usuario_id, user_id)
        self.assertEqual(
            revoked_token.expira_en,
            datetime.fromtimestamp(1_900_000_000, tz=timezone.utc),
        )
        mock_session.commit.assert_called_once()

    def test_logout_duplicate_revocation_still_returns_200(self):
        user_id = uuid.uuid4()
        mock_session = Mock()
        mock_session.commit.side_effect = IntegrityError("dup", {}, None)

        with patch.object(
            auth_routes,
            "get_jwt",
            return_value={"jti": "token-jti", "exp": 1_900_000_000},
        ):
            with patch.object(
                auth_routes, "get_jwt_identity", return_value=str(user_id)
            ):
                with patch.object(auth_routes.db, "session", mock_session):
                    with self.app.test_request_context("/auth/logout", method="POST"):
                        response = auth_routes.logout.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        self.assertEqual(status_code, 200)
        self.assertEqual(flask_response.get_json()["mensaje"], "sesion-cerrada")
        mock_session.rollback.assert_called_once()

    def test_change_password_success_updates_hash_and_flag(self):
        user_id = uuid.uuid4()
        user = SimpleNamespace(
            id=user_id,
            estado="activo",
            password_hash="hash-viejo",
            primer_login=True,
            updated_at=None,
        )
        mock_session = Mock()
        mock_session.get.return_value = user

        with patch.object(auth_routes, "get_jwt_identity", return_value=str(user_id)):
            with patch.object(auth_routes.db, "session", mock_session):
                with patch.object(auth_routes, "verify_password", return_value=True):
                    with patch.object(
                        auth_routes,
                        "hash_password",
                        return_value="hash-nuevo",
                    ):
                        with self.app.test_request_context(
                            "/auth/change-password",
                            method="POST",
                            json={
                                "password_actual": "Temporal123",
                                "password_nueva": "NuevaSegura123",
                            },
                        ):
                            response = auth_routes.change_password.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        self.assertEqual(status_code, 200)
        self.assertEqual(
            flask_response.get_json()["mensaje"], "contrasena-actualizada"
        )
        self.assertEqual(user.password_hash, "hash-nuevo")
        self.assertFalse(user.primer_login)
        self.assertIsNotNone(user.updated_at)
        mock_session.commit.assert_called_once()

    def test_change_password_rejects_wrong_current_password(self):
        user_id = uuid.uuid4()
        user = SimpleNamespace(
            id=user_id,
            estado="activo",
            password_hash="hash-viejo",
        )
        mock_session = Mock()
        mock_session.get.return_value = user

        with patch.object(auth_routes, "get_jwt_identity", return_value=str(user_id)):
            with patch.object(auth_routes.db, "session", mock_session):
                with patch.object(auth_routes, "verify_password", return_value=False):
                    with self.app.test_request_context(
                        "/auth/change-password",
                        method="POST",
                        json={
                            "password_actual": "incorrecta",
                            "password_nueva": "NuevaSegura123",
                        },
                    ):
                        response = auth_routes.change_password.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        self.assertEqual(status_code, 401)
        self.assertEqual(
            flask_response.get_json()["error"], "credenciales-invalidas"
        )

    def test_change_password_rejects_invalid_payload(self):
        with self.app.test_request_context(
            "/auth/change-password",
            method="POST",
            json={"password_actual": "Temporal123"},
        ):
            response = auth_routes.change_password.__wrapped__()

        flask_response, status_code = _unwrap_response(response)
        self.assertEqual(status_code, 400)
        self.assertEqual(flask_response.get_json()["error"], "datos-invalidos")


class AuthJwtCallbacksTests(unittest.TestCase):
    """Verifica respuestas basicas de callbacks JWT registrados en la app."""

    def setUp(self) -> None:
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_logout_without_token_returns_token_invalido(self):
        response = self.client.post("/auth/logout")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "token-invalido")

    def test_logout_with_malformed_token_returns_token_invalido(self):
        response = self.client.post(
            "/auth/logout",
            headers={"Authorization": "Bearer token-malformado"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "token-invalido")


if __name__ == "__main__":
    unittest.main()
