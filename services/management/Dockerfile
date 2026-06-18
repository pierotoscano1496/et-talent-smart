# Servicio_Gestion — puerto 5003
# Cumple: Requirements 9.1, 9.3

FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente del servicio
COPY . .

# Puerto del servicio de gestión
ENV PORT=5003

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=3 --start-period=20s \
    CMD curl -f http://localhost:${PORT}/management/health || exit 1

# Arrancar con gunicorn
CMD gunicorn --bind 0.0.0.0:${PORT} --workers 2 --timeout 30 wsgi:app
