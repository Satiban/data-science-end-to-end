FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 1. Dependencias fijadas primero (aprovecha la caché de Docker)
COPY servicio/requirements.txt ./servicio/requirements.txt
RUN pip install --no-cache-dir -r ./servicio/requirements.txt

# 2. Pipeline compartido (importado, no copiado) y código del servicio
COPY modelado/pipeline_proyecto.py ./modelado/pipeline_proyecto.py
COPY servicio/ ./servicio/

EXPOSE 8000

CMD ["uvicorn", "servicio.api:app", "--host", "0.0.0.0", "--port", "8000"]