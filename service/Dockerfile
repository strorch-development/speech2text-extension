FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir --no-deps . \
    && pip install --no-cache-dir \
        "fastapi>=0.110" \
        "uvicorn[standard]>=0.27" \
        "faster-whisper>=1.0.0"

ARG WHISPER_MODEL=small.en
ARG WHISPER_COMPUTE_TYPE=int8
ARG PRELOAD_WHISPER_MODEL=0
RUN if [ "$PRELOAD_WHISPER_MODEL" = "1" ]; then \
        python -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODEL}', device='cpu', compute_type='${WHISPER_COMPUTE_TYPE}')"; \
    fi

CMD ["speech2text-extension-remote-server"]
