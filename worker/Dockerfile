# ============================================
# Dockerfile para Worker Outbox (Opcional - si decides separarlo)
# ============================================
# NOTA: Actualmente el worker está integrado en la app.
# Este Dockerfile es para si quieres ejecutarlo como servicio separado.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copiar solo lo necesario para el worker
COPY config.py .
COPY app/ ./app/
COPY worker/ ./worker/

# Crear script de entrada
RUN echo '#!/bin/bash\n\
echo "Iniciando Outbox Worker..."\n\
python -c "from app import create_app; from worker.outbox_worker import init_worker; app = create_app(); init_worker(app); import time; \n\
while True: time.sleep(1)"\n\
' > /app/start_worker.sh && chmod +x /app/start_worker.sh

# Usuario no-root
RUN useradd -m -u 1000 workeruser && \
    chown -R workeruser:workeruser /app
USER workeruser

CMD ["/app/start_worker.sh"]