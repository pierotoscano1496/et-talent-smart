"""
Modelos de solo lectura del Servicio_Reportes.
Importar desde aquí para facilitar el descubrimiento de tablas por SQLAlchemy.
"""
from .evento_acceso import EventoAcceso
from .estudiante import Estudiante
from .ambiente import Ambiente
from .nodo_acceso import NodoAcceso
from .token_revocado import TokenRevocado

__all__ = ["EventoAcceso", "Estudiante", "Ambiente", "NodoAcceso"]
