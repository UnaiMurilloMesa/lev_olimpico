FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# ffmpeg: transcodificacion a H.264 compatible con Android
# libglib2.0-0: dependencia de OpenCV
# libportaudio2: mediapipe importa sounddevice y falla sin PortAudio
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libglib2.0-0 \
        libportaudio2 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Modelo de pose embebido en la imagen (evita descargas en runtime)
RUN mkdir -p /app/models && \
    curl -fSL "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task" \
      -o /app/models/pose_landmarker_heavy.task

RUN useradd --create-home --uid 1000 appuser && \
    mkdir -p /app/storage && chown -R appuser:appuser /app

# --- Etapa de produccion: solo el codigo de la aplicacion ---
FROM base AS production

COPY app ./app
RUN chown -R appuser:appuser /app/app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# --- Etapa de desarrollo: herramientas de prueba y calidad ---
FROM base AS development

COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

COPY pyproject.toml .
COPY app ./app
COPY tests ./tests
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]