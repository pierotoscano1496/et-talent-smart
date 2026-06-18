"""
Importaciones de todos los modelos del Servicio_Acceso.

Importar este módulo garantiza que SQLAlchemy registre todos los
mappers antes de que se creen o migren las tablas.
"""
from models.nodo_acceso import NodoAcceso  # noqa: F401
from models.ambiente import Ambiente  # noqa: F401
from models.token_nodo import TokenNodo  # noqa: F401
from models.evento_acceso import EventoAcceso  # noqa: F401
from models.tag_rfid import TagRFID  # noqa: F401
from models.estudiante import Estudiante  # noqa: F401
from models.bitacora_seguridad import BitacoraSeguridad  # noqa: F401
from models.token_revocado import TokenRevocado  # noqa: F401
