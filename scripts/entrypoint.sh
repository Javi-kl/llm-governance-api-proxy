#!/bin/bash
# entrypoint.sh — Ejecuta migraciones y arranca la aplicación
# Se ejecuta DENTRO del contenedor antes de que uvicorn arranque.
# Si alembic falla, el contenedor muere (exit 1) — no arranca app con schema viejo.

set -e  # Salir inmediatamente si cualquier comando falla

echo "Running migrations..."
alembic upgrade head

echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
