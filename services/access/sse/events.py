"""
Canal SSE interno para el Servicio_Acceso.

Provee un mecanismo hilo-seguro para publicar eventos de acceso y
de estado de nodo a todos los clientes SSE suscritos.

Uso:
    from services.access.sse.events import sse_channel

    # Publicar un evento (desde cualquier hilo)
    sse_channel.publish({"evento_id": "...", "resultado": "autorizado", ...})

    # Suscribirse al canal (desde el handler SSE)
    for data in sse_channel.subscribe():
        yield f"data: {json.dumps(data)}\n\n"

Cumple: Requirements 5.1, 5.2, 3.8
"""
import json
import logging
import queue
import threading
from typing import Generator

logger = logging.getLogger(__name__)

# Tamaño máximo de cada cola de suscriptor.
# Si el cliente no consume a tiempo, los mensajes más antiguos se descartan.
_MAX_QUEUE_SIZE = 100


class SSEChannel:
    """
    Canal de distribución de eventos Server-Sent Events (SSE).

    Mantiene una lista de colas (una por suscriptor activo) y entrega
    cada evento publicado a todas ellas de forma hilo-segura.

    Atributos de clase:
        _lock  – protege el acceso concurrente a _subscribers.
        _subscribers – lista de colas activas.
    """

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._subscribers: list[queue.Queue] = []

    # ── Publicar ─────────────────────────────────────────────────────────────

    def publish(self, data: dict) -> None:
        """
        Publica un evento a todos los suscriptores activos.

        Si la cola de un suscriptor está llena, el evento más antiguo se
        descarta (política LIFO no adoptada; se usa put_nowait para no
        bloquear el hilo del Servicio_Acceso).

        Args:
            data: Diccionario con los campos del evento a enviar.
        """
        with self._lock:
            dead: list[queue.Queue] = []
            for q in self._subscribers:
                try:
                    q.put_nowait(data)
                except queue.Full:
                    # Descartar el más antiguo y reintentar
                    try:
                        q.get_nowait()
                        q.put_nowait(data)
                    except (queue.Empty, queue.Full):
                        logger.warning(
                            "SSEChannel: cola llena para suscriptor; evento descartado"
                        )
            # Eliminar suscriptores muertos (cola cerrada no es detectabledirectamente;
            # la limpieza ocurre en unsubscribe)

    # ── Suscribirse ──────────────────────────────────────────────────────────

    def subscribe(self, timeout: float = 30.0) -> Generator[dict, None, None]:
        """
        Suscribe al canal y genera eventos a medida que llegan.

        Este generador debe usarse dentro de un contexto de streaming HTTP
        (p.ej. Flask Response con stream_with_context). El generador
        termina cuando el suscriptor se desconecta (el caller deja de
        iterar).

        Args:
            timeout: Segundos máximos de espera en cada iteración antes de
                     re-chequear (permite detectar desconexión del cliente).

        Yields:
            dict: Payload del evento publicado.
        """
        q: queue.Queue = queue.Queue(maxsize=_MAX_QUEUE_SIZE)
        with self._lock:
            self._subscribers.append(q)
        logger.debug("SSEChannel: nuevo suscriptor (total=%d)", len(self._subscribers))
        try:
            while True:
                try:
                    data = q.get(timeout=timeout)
                    yield data
                except queue.Empty:
                    # Yield None como heartbeat para mantener la conexión viva;
                    # el caller debe ignorar los None.
                    yield {}
        finally:
            self._unsubscribe(q)

    def _unsubscribe(self, q: queue.Queue) -> None:
        """Elimina la cola del suscriptor de la lista activa."""
        with self._lock:
            try:
                self._subscribers.remove(q)
                logger.debug(
                    "SSEChannel: suscriptor eliminado (total=%d)",
                    len(self._subscribers),
                )
            except ValueError:
                pass

    @property
    def subscriber_count(self) -> int:
        """Número de suscriptores activos (útil para métricas/tests)."""
        with self._lock:
            return len(self._subscribers)


# Instancia singleton compartida por el proceso
sse_channel: SSEChannel = SSEChannel()
