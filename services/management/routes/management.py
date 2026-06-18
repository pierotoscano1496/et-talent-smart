"""Endpoints del Servicio_Gestion."""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from authz import roles_required
from extensions import db
from models.ambiente import Ambiente
from models.estudiante import Estudiante
from models.nodo_acceso import NodoAcceso
from models.tag_rfid import TagRFID
from models.token_nodo import TokenNodo
from models.usuario_web import UsuarioWeb
from utils import hash_password

_CODIGO_RE = re.compile(r"^[A-Za-z0-9]+$")
_NODE_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9-]+$")
_RFID_RE = re.compile(r"^[0-9A-F]{8}$")
_ESTADOS_VALIDOS = {"activo", "inactivo"}
_ROLES_VALIDOS = {"ADMINISTRADOR", "AUXILIAR_EDUCACION"}


def _json_error(code: str, status: int):
    return jsonify({"error": code}), status


def _parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def _pagination_params() -> tuple[int, int]:
    try:
        page = max(int(request.args.get("page", 1)), 1)
        page_size = int(request.args.get("page_size", 50))
    except (TypeError, ValueError):
        return 1, 50

    return page, min(max(page_size, 1), 100)


def _touch(model) -> None:
    if hasattr(model, "updated_at"):
        model.updated_at = datetime.now(timezone.utc)


def _student_payload(student: Estudiante) -> dict:
    payload = student.to_dict()
    active_tag = student.tag_activo
    payload["tag_rfid"] = active_tag.uid_hex if active_tag else None
    return payload


def _environment_payload(environment: Ambiente) -> dict:
    return environment.to_dict()


def _node_payload(node: NodoAcceso) -> dict:
    payload = node.to_dict()
    payload["ambiente_nombre"] = node.ambiente.nombre if node.ambiente else None
    active_token = next((token for token in node.tokens if token.estado == "activo"), None)
    payload["token_activo"] = active_token is not None
    return payload


def _user_payload(user: UsuarioWeb) -> dict:
    return user.to_dict()


def _normalized_state(raw_value: str | None, *, default: str = "activo") -> str | None:
    value = (raw_value or default).strip().lower()
    if value not in _ESTADOS_VALIDOS:
        return None
    return value


def _commit_or_500():
    try:
        db.session.commit()
        return None
    except SQLAlchemyError:
        db.session.rollback()
        return _json_error("error-interno", 500)


# ---- Estudiantes ----
students_bp = Blueprint("students", __name__)


@students_bp.post("/management/students")
@roles_required("ADMINISTRADOR")
def create_student():
    payload = request.get_json(silent=True) or {}

    nombre_completo = (payload.get("nombre_completo") or "").strip()
    codigo = (payload.get("codigo") or "").strip()
    grado_seccion = (payload.get("grado_seccion") or "").strip()
    estado = _normalized_state(payload.get("estado"), default="activo")

    if (
        not nombre_completo
        or len(nombre_completo) > 100
        or not codigo
        or len(codigo) > 20
        or not _CODIGO_RE.fullmatch(codigo)
        or not grado_seccion
        or len(grado_seccion) > 20
        or estado is None
    ):
        return _json_error("payload-invalido", 400)

    if (
        db.session.query(Estudiante.id)
        .filter(func.lower(Estudiante.codigo) == codigo.lower())
        .first()
        is not None
    ):
        return _json_error("codigo-duplicado", 409)

    student = Estudiante(
        nombre_completo=nombre_completo,
        codigo=codigo,
        grado_seccion=grado_seccion,
        estado=estado,
    )
    db.session.add(student)

    error_response = _commit_or_500()
    if error_response:
        return error_response

    return jsonify(_student_payload(student)), 201


@students_bp.get("/management/students")
@roles_required("ADMINISTRADOR")
def list_students():
    page, page_size = _pagination_params()
    query = Estudiante.query.order_by(Estudiante.created_at.desc())
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)

    return jsonify(
        {
            "data": [_student_payload(student) for student in pagination.items],
            "total": pagination.total,
            "page": page,
            "page_size": page_size,
        }
    )


@students_bp.patch("/management/students/<string:student_id>")
@roles_required("ADMINISTRADOR")
def update_student(student_id: str):
    student_uuid = _parse_uuid(student_id)
    if student_uuid is None:
        return _json_error("estudiante-no-encontrado", 404)

    student = Estudiante.query.get(student_uuid)
    if student is None:
        return _json_error("estudiante-no-encontrado", 404)

    payload = request.get_json(silent=True) or {}

    if "nombre_completo" in payload:
        nombre_completo = (payload.get("nombre_completo") or "").strip()
        if not nombre_completo or len(nombre_completo) > 100:
            return _json_error("payload-invalido", 400)
        student.nombre_completo = nombre_completo

    if "grado_seccion" in payload:
        grado_seccion = (payload.get("grado_seccion") or "").strip()
        if not grado_seccion or len(grado_seccion) > 20:
            return _json_error("payload-invalido", 400)
        student.grado_seccion = grado_seccion

    if "estado" in payload:
        estado = _normalized_state(payload.get("estado"), default="")
        if estado is None:
            return _json_error("payload-invalido", 400)
        student.estado = estado

    _touch(student)
    error_response = _commit_or_500()
    if error_response:
        return error_response

    return jsonify(_student_payload(student))


@students_bp.post("/management/students/<string:student_id>/rfid")
@roles_required("ADMINISTRADOR")
def assign_rfid(student_id: str):
    student_uuid = _parse_uuid(student_id)
    if student_uuid is None:
        return _json_error("estudiante-no-encontrado", 404)

    student = Estudiante.query.get(student_uuid)
    if student is None:
        return _json_error("estudiante-no-encontrado", 404)

    payload = request.get_json(silent=True) or {}
    uid_hex = (payload.get("uid_hex") or payload.get("tag_rfid") or "").strip().upper()
    if not _RFID_RE.fullmatch(uid_hex):
        return _json_error("payload-invalido", 400)

    existing_tag = TagRFID.query.filter_by(uid_hex=uid_hex).first()
    if existing_tag is not None and existing_tag.estudiante_id != student.id:
        return _json_error("tag-en-uso", 409)

    active_tag = student.tag_activo
    if active_tag is not None and active_tag.uid_hex != uid_hex:
        active_tag.activo = False
        active_tag.desasignado_en = datetime.now(timezone.utc)

    if existing_tag is None:
        existing_tag = TagRFID(
            uid_hex=uid_hex,
            estudiante_id=student.id,
            activo=True,
            desasignado_en=None,
        )
        db.session.add(existing_tag)
    else:
        existing_tag.estudiante_id = student.id
        existing_tag.activo = True
        existing_tag.desasignado_en = None
        existing_tag.asignado_en = datetime.now(timezone.utc)

    _touch(student)
    error_response = _commit_or_500()
    if error_response:
        return error_response

    return jsonify(_student_payload(student))


# ---- Ambientes ----
environments_bp = Blueprint("environments", __name__)


@environments_bp.post("/management/environments")
@roles_required("ADMINISTRADOR")
def create_environment():
    payload = request.get_json(silent=True) or {}

    nombre = (payload.get("nombre") or "").strip()
    descripcion = (payload.get("descripcion") or "").strip()
    ubicacion = (payload.get("ubicacion") or "").strip()
    estado = _normalized_state(payload.get("estado"), default="activo")

    if (
        not nombre
        or len(nombre) > 80
        or len(descripcion) > 255
        or len(ubicacion) > 120
        or estado is None
    ):
        return _json_error("payload-invalido", 400)

    if (
        db.session.query(Ambiente.id)
        .filter(func.lower(Ambiente.nombre) == nombre.lower())
        .first()
        is not None
    ):
        return _json_error("nombre-ambiente-duplicado", 409)

    environment = Ambiente(
        nombre=nombre,
        descripcion=descripcion,
        ubicacion=ubicacion,
        estado=estado,
    )
    db.session.add(environment)

    error_response = _commit_or_500()
    if error_response:
        return error_response

    return jsonify(_environment_payload(environment)), 201


@environments_bp.get("/management/environments")
@roles_required("ADMINISTRADOR")
def list_environments():
    page, page_size = _pagination_params()
    query = Ambiente.query.order_by(Ambiente.created_at.desc())
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)

    return jsonify(
        {
            "data": [_environment_payload(environment) for environment in pagination.items],
            "total": pagination.total,
            "page": page,
            "page_size": page_size,
        }
    )


# ---- Nodos de acceso ----
nodes_bp = Blueprint("nodes", __name__)


@nodes_bp.post("/management/nodes")
@roles_required("ADMINISTRADOR")
def create_node():
    payload = request.get_json(silent=True) or {}

    identificador = (payload.get("identificador") or "").strip()
    descripcion = (payload.get("descripcion") or "").strip()
    estado = _normalized_state(payload.get("estado"), default="activo")
    ambiente_raw = payload.get("id_ambiente") or payload.get("ambiente_id")
    ambiente_uuid = _parse_uuid(ambiente_raw)

    if (
        not identificador
        or len(identificador) > 40
        or not _NODE_IDENTIFIER_RE.fullmatch(identificador)
        or len(descripcion) > 255
        or estado is None
        or ambiente_uuid is None
    ):
        return _json_error("payload-invalido", 400)

    if (
        db.session.query(NodoAcceso.id)
        .filter(func.lower(NodoAcceso.identificador) == identificador.lower())
        .first()
        is not None
    ):
        return _json_error("identificador-nodo-duplicado", 409)

    environment = Ambiente.query.get(ambiente_uuid)
    if environment is None:
        return _json_error("ambiente-no-encontrado", 422)

    node = NodoAcceso(
        identificador=identificador,
        descripcion=descripcion,
        estado=estado,
        ambiente_id=environment.id,
    )
    db.session.add(node)

    error_response = _commit_or_500()
    if error_response:
        return error_response

    return jsonify(_node_payload(node)), 201


@nodes_bp.patch("/management/nodes/<string:node_id>/status")
@roles_required("ADMINISTRADOR")
def update_node_status(node_id: str):
    node_uuid = _parse_uuid(node_id)
    if node_uuid is None:
        return _json_error("nodo-no-encontrado", 404)

    node = NodoAcceso.query.get(node_uuid)
    if node is None:
        return _json_error("nodo-no-encontrado", 404)

    payload = request.get_json(silent=True) or {}
    estado = _normalized_state(payload.get("estado"), default="")
    if estado is None:
        return _json_error("payload-invalido", 400)

    node.estado = estado
    _touch(node)

    error_response = _commit_or_500()
    if error_response:
        return error_response

    return jsonify(_node_payload(node))


@nodes_bp.post("/management/nodes/<string:node_id>/token")
@roles_required("ADMINISTRADOR")
def manage_node_token(node_id: str):
    node_uuid = _parse_uuid(node_id)
    if node_uuid is None:
        return _json_error("nodo-no-encontrado", 404)

    node = NodoAcceso.query.get(node_uuid)
    if node is None:
        return _json_error("nodo-no-encontrado", 404)

    payload = request.get_json(silent=True) or {}
    action = (payload.get("action") or "generate").strip().lower()
    if action not in {"generate", "revoke", "regenerate"}:
        return _json_error("payload-invalido", 400)

    active_tokens = TokenNodo.query.filter_by(nodo_id=node.id, estado="activo").all()
    now = datetime.now(timezone.utc)

    for token in active_tokens:
        token.estado = "revocado"
        token.revocado_en = now

    response_payload = {
        "nodo_id": str(node.id),
        "accion": action,
        "estado_token": "revocado",
    }

    if action in {"generate", "regenerate"}:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        db.session.add(
            TokenNodo(
                nodo_id=node.id,
                token_hash=token_hash,
                estado="activo",
            )
        )
        response_payload["estado_token"] = "activo"
        response_payload["token"] = raw_token

    error_response = _commit_or_500()
    if error_response:
        return error_response

    return jsonify(response_payload)


# ---- Usuarios web ----
users_bp = Blueprint("users", __name__)


@users_bp.post("/management/users")
@roles_required("ADMINISTRADOR")
def create_user():
    payload = request.get_json(silent=True) or {}

    nombre_completo = (payload.get("nombre_completo") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = (payload.get("password_temporal") or payload.get("password") or "").strip()
    rol = (payload.get("rol") or "").strip().upper()
    estado = _normalized_state(payload.get("estado"), default="activo")

    if (
        not nombre_completo
        or len(nombre_completo) > 100
        or not email
        or len(email) > 254
        or "@" not in email
        or not password
        or len(password) > 255
        or rol not in _ROLES_VALIDOS
        or estado is None
    ):
        return _json_error("payload-invalido", 400)

    if (
        db.session.query(UsuarioWeb.id)
        .filter(func.lower(UsuarioWeb.email) == email.lower())
        .first()
        is not None
    ):
        return _json_error("email-duplicado", 409)

    user = UsuarioWeb(
        nombre_completo=nombre_completo,
        email=email,
        password_hash=hash_password(password),
        rol=rol,
        estado=estado,
        primer_login=True,
    )
    db.session.add(user)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _json_error("email-duplicado", 409)
    except SQLAlchemyError:
        db.session.rollback()
        return _json_error("error-interno", 500)

    return jsonify(_user_payload(user)), 201


@users_bp.patch("/management/users/<string:user_id>")
@roles_required("ADMINISTRADOR")
def update_user(user_id: str):
    user_uuid = _parse_uuid(user_id)
    if user_uuid is None:
        return _json_error("usuario-no-encontrado", 404)

    user = UsuarioWeb.query.get(user_uuid)
    if user is None:
        return _json_error("usuario-no-encontrado", 404)

    payload = request.get_json(silent=True) or {}

    if "rol" in payload:
        rol = (payload.get("rol") or "").strip().upper()
        if rol not in _ROLES_VALIDOS:
            return _json_error("payload-invalido", 400)
        user.rol = rol

    if "estado" in payload:
        estado = _normalized_state(payload.get("estado"), default="")
        if estado is None:
            return _json_error("payload-invalido", 400)
        user.estado = estado

    _touch(user)
    error_response = _commit_or_500()
    if error_response:
        return error_response

    return jsonify(_user_payload(user))
