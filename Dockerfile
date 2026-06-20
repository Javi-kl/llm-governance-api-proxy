
# IMAGEN BASE
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim-bookworm


# DEPENDENCIAS DEL SISTEMA
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    pkg-config && \
    rm -rf /var/lib/apt/lists/*


# Crear usuario sin privilegios
RUN useradd --create-home --shell /bin/bash appuser


# DIRECTORIO DE TRABAJO
WORKDIR /app


# DEPENDENCIAS PYTHON
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# CÓDIGO FUENTE
COPY . .


RUN chmod +x /app/scripts/entrypoint.sh \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

ENTRYPOINT [ "/app/scripts/entrypoint.sh" ]
