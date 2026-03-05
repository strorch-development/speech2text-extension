# Remote GPU server (optional)

This service package can also run a small HTTP server to host Whisper on a separate machine (e.g. a desktop with an NVIDIA GPU). The GNOME extension continues to use the D-Bus service on your laptop, but the D-Bus service forwards recorded WAV audio to the remote server.

## Server: run on the GPU machine

Install with the server extra:

```bash
pip install "speech2text-extension-service[server]"
```

Start the server:

```bash
# Binds to 0.0.0.0:8090 by default
speech2text-extension-remote-server --model large-v3 --device cuda --port 8090

# Optional: require an API key
SPEECH2TEXT_SERVER_API_KEY='change-me' speech2text-extension-remote-server --model large-v3 --device cuda
```

Health check:

```bash
curl -s http://127.0.0.1:8090/health | jq
```

API:

- `POST /v1/transcribe`
  - Request body: raw WAV bytes (`Content-Type: audio/wav`)
  - Optional auth header: `X-Api-Key: ...`
  - Response: JSON `{ "text": "..." }`

## Client: configure on the GNOME laptop

Enable remote mode in GNOME settings:

```bash
gsettings set org.gnome.shell.extensions.speech2text remote-enabled true
gsettings set org.gnome.shell.extensions.speech2text remote-url 'http://<GPU_MACHINE_IP>:8090'
# Optional, if server uses an API key:
gsettings set org.gnome.shell.extensions.speech2text remote-api-key 'change-me'
```

Then restart the D-Bus service (or restart GNOME Shell):

- X11: `Alt+F2` → `r` → Enter
- Wayland: log out/in

## Security note

Do **not** expose this server to the public Internet as-is. Prefer:

- LAN-only binding, or
- an SSH tunnel (`ssh -L 8090:127.0.0.1:8090 gpu-box`), or
- a firewall rule limiting access to your laptop’s IP.
