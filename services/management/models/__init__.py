"""
Importa todos los modelos SQLAlchemy del Servicio_Gestion para que
SQLAlchemy los registre al inicializar la app.
"""
from .usuario_web import UsuarioWeb  # noqa: F401
from .estudiante import Estudiante  # noqa: F401
from .tag_rfid import TagRFID  # noqa: F401
from .ambiente import Ambiente  # noqa: F401
from .nodo_acceso import NodoAcceso  # noqa: F401
from .token_nodo import TokenNodo  # noqa: F401
from .token_revocado import TokenRevocado  # noqa: F401
from .evento_acceso import EventoAcceso  # noqa: F401
