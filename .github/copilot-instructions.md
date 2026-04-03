# Copilot Instructions — speech2text-extension

## Architecture

This repo has **two independent components** that must be developed and versioned separately:

### 1. GNOME Extension (`src/`)
JavaScript (GJS) GNOME Shell extension. Provides the panel icon, keyboard shortcut, and all UI dialogs. It is **deliberately lightweight** — no audio, no ML. It communicates with the service exclusively over **D-Bus** using the `org.gnome.Shell.Extensions.Speech2Text` interface defined in `src/lib/dbusManager.js`.

- Entry point: `src/extension.js` — creates and wires `ServiceManager`, `UIManager`, `RecordingController`, `KeybindingManager`
- Module layer: `src/lib/` — each file owns one concern (dbus, ui, state, keybinding, etc.)
- Settings: GSettings schema `org.gnome.shell.extensions.speech2text` (`src/schemas/`)
- GJS imports use `gi://` syntax (e.g. `gi://Gio`, `gi://GLib`) and `resource:///org/gnome/shell/...`
- Extension UUID (from `src/metadata.json`): `gnome-speech2text@kaveh.page`

### 2. D-Bus Service (`service/`)
Python package `speech2text-extension-service`. Handles audio capture (FFmpeg), local Whisper transcription, text insertion (xdotool/clipboard), and optional remote GPU forwarding. Runs as a D-Bus session service auto-activated by D-Bus.

- Main service: `service/src/gnome_speech2text_service/service.py` — asyncio + `dbus-next`
- Entry points (via `pyproject.toml`):
  - `speech2text-extension-service` → `cli:main`
  - `speech2text-extension-remote-server` → `remote_server.py:main` (optional FastAPI, `[server]` extra)
- D-Bus bus name: `org.gnome.Shell.Extensions.Speech2Text`
- Object path: `/org/gnome/Shell/Extensions/Speech2Text`
- Service installs to `~/.local/share/speech2text-extension-service/` (venv included)
- D-Bus service file registered at `~/.local/share/dbus-1/services/`

### D-Bus Interface (source of truth: `src/lib/dbusManager.js`)
Methods: `StartRecording`, `StopRecording`, `CancelRecording`, `TypeText`, `SetWhisperConfig`, `SetRemoteConfig`, `GetServiceStatus`, `CheckDependencies`  
Signals: `RecordingStarted`, `RecordingStopped`, `TranscriptionReady`, `RecordingError`

Python service uses `dbus-next` type annotations as string literals (`'s'`, `'b'`, `'i'`, `'as'`) — not Python types. Static type checkers may flag these; the forward-reference stubs in `service.py` are intentional.

## Build & Install Commands

```bash
# Install extension files + compile GSettings schemas
make install

# Full fresh setup (clean + install + service)
make setup

# Create distribution ZIP for GNOME Extensions store (output: dist/)
make package

# Check installation health
make status

# Install D-Bus service only (from local source)
service/install-service.sh

# Install D-Bus service from PyPI (non-interactive)
curl -sSL .../install-service.sh | bash -s -- --pypi --non-interactive --service-version 1.2.0 --whisper-model base

# Install with GPU support
./service/install-service.sh --gpu

# Use a specific Python version for the service venv
make install-service PYTHON=python3.12
```

After schema changes, always recompile: `glib-compile-schemas ~/.local/share/gnome-shell/extensions/gnome-speech2text@kaveh.page/schemas/`

After extension JS changes, restart GNOME Shell:
- X11: `Alt+F2` → `r` → Enter
- Wayland: log out and back in

## Debugging

```bash
# Live extension + service logs
journalctl -f | grep -E "(gnome-shell|speech2text-extension-service|speech2text|ffmpeg|org\.gnome\.Speech2Text|Whisper|transcrib)"

# Service-only logs
journalctl --user -u speech2text-service

# Test D-Bus interface directly
dbus-send --session --dest=org.gnome.Shell.Extensions.Speech2Text \
  --print-reply /org/gnome/Shell/Extensions/Speech2Text \
  org.gnome.Shell.Extensions.Speech2Text.GetServiceStatus

# Crash diagnostics
./debug-crash.sh
```

## Key Conventions

- **D-Bus is the only IPC** — the extension never imports Python or runs subprocesses directly. All service interaction goes through `DBusManager` → `ServiceManager`.
- **Service installer writes `install-state.conf`** — `ServiceManager._hasInstallerMarker()` checks for this file; without it the extension shows a setup dialog. Never skip the installer when testing locally.
- **`src/lib/constants.js`** defines all shared colors (`COLORS.*`) and inline CSS strings (`STYLES.*`). Use these instead of hardcoding style strings in UI files.
- **Extension package excludes `install-service.sh`** — the `make package` target removes it from the zip; the extension downloads it from GitHub at runtime. Do not bundle it.
- **Schema changes need recompilation** — adding/removing GSettings keys requires `glib-compile-schemas` before the extension picks them up.
- **Whisper device values**: internally `"cpu"` or `"gpu"` (maps to `"cuda"` in Whisper API). Switching CPU↔GPU requires reinstalling the service venv from scratch.
- **Remote server** (`remote_server.py`) is a FastAPI app; install with `pip install "speech2text-extension-service[server]"`. Its API: `POST /v1/transcribe` (raw WAV body → `{"text": "..."}`) and `GET /health`.
- **Python version constraint**: 3.8–3.13 (3.14+ not supported due to ML dependencies). The service venv is self-contained; no system `python3-dbus` or `python3-gi` needed.

## Remote Deployment

Generic container files live in `service/` (`Dockerfile`, `.dockerignore`, `docker-compose.yml`, `.env.example`).
Private deployment notes and provider-specific scripts stay outside the tracked repository.
