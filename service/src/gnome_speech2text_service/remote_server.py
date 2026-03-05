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
    Response: {"status": "ok", "model": "...", "device": "cpu|cuda"}
"""

import argparse
import os
import sys
import syslog
import tempfile
import threading
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

import whisper


_model = None
_model_lock = threading.Lock()
_transcribe_lock = threading.Lock()


def _load_model(model_name: str, device: str):
    global _model
    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        syslog.syslog(syslog.LOG_INFO, f"Loading Whisper model: {model_name} ({device})")
        _model = whisper.load_model(model_name, device=device)
        syslog.syslog(syslog.LOG_INFO, "Whisper model loaded")
        return _model


def create_app(model_name: str, device: str, api_key: Optional[str]):
    app = FastAPI(title="speech2text-extension-remote-server")

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "model": model_name,
            "device": device,
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

        # Whisper expects a filename; write to a temp WAV.
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(body)
            wav_path = tmp.name

        try:
            model = _load_model(model_name, device)
            # Whisper model is heavy; keep only 1 transcription at a time by default.
            with _transcribe_lock:
                result = model.transcribe(wav_path, fp16=(device == "cuda"))
            text = str(result.get("text") or "").strip()
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
        # Avoid leaking internals; log to syslog.
        syslog.syslog(syslog.LOG_ERR, f"Unhandled error: {exc}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Speech2Text remote Whisper server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8090, help="Bind port (default: 8090)")
    parser.add_argument(
        "--model",
        default="medium",
        help="Whisper model to load (default: medium; consider large-v3 on strong GPUs)",
    )
    parser.add_argument(
        "--device",
        choices=["cpu", "cuda"],
        default="cuda",
        help="Device to use (cpu|cuda). Default: cuda",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("SPEECH2TEXT_SERVER_API_KEY", ""),
        help="Optional API key to require (also via SPEECH2TEXT_SERVER_API_KEY env)",
    )
    args = parser.parse_args(argv)

    # syslog for consistency with the D-Bus service.
    syslog.openlog("speech2text-remote-server", syslog.LOG_PID, syslog.LOG_USER)

    api_key = (args.api_key or "").strip() or None

    app = create_app(args.model, args.device, api_key)

    # Import uvicorn lazily so the module can be imported without server extras.
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
