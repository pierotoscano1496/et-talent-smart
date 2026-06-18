"""
Entrypoint WSGI del Servicio_Reportes.

Gunicorn arranca el servidor usando:
    gunicorn --bind 0.0.0.0:5004 wsgi:app

Cumple: Requirements 9.1, 9.3
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
