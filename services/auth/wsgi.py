"""
Punto de entrada WSGI para el Servicio_Autenticacion.

Gunicorn arranca el servidor apuntando a este módulo:
  gunicorn --bind 0.0.0.0:5001 wsgi:app

Cumple: Requirements 9.1
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Uso directo (desarrollo): python wsgi.py
    app.run(host="0.0.0.0", port=5001, debug=False)
