#!/usr/bin/env python3

"""Remote transcription server for Speech2Text.

This is an optional HTTP server that runs Whisper on a (potentially GPU-equipped)
machine and serves transcriptions to other computers on the network.

API:
  POST /v1/transcribe
    Body: raw WAV bytes (Content-Type: audio/wav)
    Header: X-Api-Key (optional)
    Response: {"text": "..."}

  GET /health
    Response: {"status": "ok", "model": "...", "device": "cpu|cuda", "compute_type": "..."}
"""

import argparse
import os
import sys
import syslog
import tempfile
import threading
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel


_model: Optional[WhisperModel] = None
_model_lock = threading.Lock()
_transcribe_lock = threading.Lock()


def _load_model(model_name: str, device: str, compute_type: str) -> WhisperModel:
    global _model
    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        syslog.syslog(
            syslog.LOG_INFO,
            f"Loading Whisper model: {model_name} on {device} ({compute_type})",
        )
        print(f"Loading Whisper model: {model_name} on {device} ({compute_type})...")
        _model = WhisperModel(model_name, device=device, compute_type=compute_type)
        syslog.syslog(syslog.LOG_INFO, "Whisper model loaded")
        print("Whisper model loaded.")
        return _model


def create_app(model_name: str, device: str, compute_type: str, api_key: Optional[str]) -> FastAPI:

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        # Preload the model at startup so the first request is not slow.
        _load_model(model_name, device, compute_type)
        yield

    app = FastAPI(title="speech2text-extension-remote-server", lifespan=lifespan)

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "model": model_name,
            "device": device,
            "compute_type": compute_type,
        }

    @app.post("/v1/transcribe")
    async def transcribe(request: Request):
        if api_key:
            provided = request.headers.get("x-api-key")
            if not provided or provided != api_key:
                raise HTTPException(status_code=401, detail="Unauthorized")

        content_type = (request.headers.get("content-type") or "").lower()
        if "audio/wav" not in content_type and "application/octet-stream" not in content_type:
            raise HTTPException(
                status_code=415,
                detail="Unsupported content-type. Send raw WAV bytes with Content-Type: audio/wav",
            )

        body = await request.body()
        if not body:
            raise HTTPException(status_code=400, detail="Empty request body")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(body)
            wav_path = tmp.name

        try:
            model = _load_model(model_name, device, compute_type)
            # Serialize transcriptions: faster-whisper model is not thread-safe.
            # Consume the segment generator inside the lock to avoid data races.
            with _transcribe_lock:
                segments, _info = model.transcribe(wav_path)
                text = "".join(seg.text for seg in segments).strip()
            if not text:
                raise HTTPException(status_code=422, detail="Empty transcription")
            return {"text": text}
        finally:
            try:
                os.unlink(wav_path)
            except Exception:
                pass

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception):
        syslog.syslog(syslog.LOG_ERR, f"Unhandled error: {exc}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Speech2Text remote Whisper server")
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "0.0.0.0"),
        help="Bind host (env: HOST, default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8090")),
        help="Bind port (env: PORT, default: 8090)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("WHISPER_MODEL", "small.en"),
        help="Whisper model to load (env: WHISPER_MODEL, default: small.en)",
    )
    parser.add_argument(
        "--device",
        choices=["cpu", "cuda", "auto"],
        default=os.environ.get("WHISPER_DEVICE", "cpu"),
        help="Device to use (env: WHISPER_DEVICE, cpu|cuda|auto, default: cpu)",
    )
    parser.add_argument(
        "--compute-type",
        default=os.environ.get("WHISPER_COMPUTE_TYPE", "int8"),
        help="CTranslate2 compute type (env: WHISPER_COMPUTE_TYPE, default: int8; use float16 for GPU)",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("SPEECH2TEXT_SERVER_API_KEY", ""),
        help="Optional API key to require (also via SPEECH2TEXT_SERVER_API_KEY env)",
    )
    args = parser.parse_args(argv)

    syslog.openlog("speech2text-remote-server", syslog.LOG_PID, syslog.LOG_USER)

    api_key = (args.api_key or "").strip() or None

    app = create_app(args.model, args.device, args.compute_type, api_key)

    try:
        import uvicorn  # type: ignore
    except Exception as e:
        print(
            "uvicorn is required to run the server. Install with: pip install speech2text-extension-service[server]",
            file=sys.stderr,
        )
        print(str(e), file=sys.stderr)
        return 2

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
