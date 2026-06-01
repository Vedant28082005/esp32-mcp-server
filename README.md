# ESP32 MCP Server

MCP server that controls an ESP32 board over HTTP (LED on/off/status), with optional ngrok exposure for Claude.ai remote integration.

## Firmware (ESP32)

Sketch: `firmware/esp32_led_bridge/esp32_led_bridge.ino`

1. Open the folder in Arduino IDE or PlatformIO.
2. Copy `firmware/esp32_led_bridge/secrets.h.example` to `secrets.h`.
3. Set `WIFI_SSID` and `WIFI_PASSWORD` in `secrets.h` (this file is not committed).
4. Flash the board and note the IP printed on Serial Monitor (`115200` baud).
5. Set that IP as `ESP32_IP` in your Python `.env`.

HTTP endpoints: `/led/on`, `/led/off`, `/led/toggle`, `/led/status`

## MCP server setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your ESP32 IP and optional ngrok URL
python src/server.py
```

## Configuration

| Variable | Description |
|----------|-------------|
| `ESP32_IP` | ESP32 address on your LAN (default `192.168.1.100`) |
| `ESP32_TIMEOUT` | HTTP timeout in seconds |
| `NGROK_URL` | Public HTTPS URL from ngrok (optional) |
| `OAUTH_CLIENT_ID` | OAuth client id for Claude.ai stub |
| `OAUTH_CLIENT_SECRET` | OAuth client secret — set a strong value |
| `OAUTH_ACCESS_TOKEN` | Bearer token returned by `/oauth/token` |

Never commit `.env`. Only `.env.example` belongs in git.

## Claude.ai integration

**Local:** Settings → Integrations → Add custom integration:

`http://127.0.0.1:8000/sse`

**Remote (ngrok):** Set `NGROK_URL` in `.env`, run ngrok to port 8000, then use `{NGROK_URL}/sse` in Claude.ai.

## Security

- **Python:** IPs, ngrok URLs, and OAuth values live in `.env` (see `.env.example`).
- **Firmware:** WiFi credentials live in `secrets.h` (see `secrets.h.example`). Never commit `secrets.h` or `.env`.
- Replace default OAuth secrets before exposing the MCP server on the internet.
- The bundled OAuth flow is a development stub, not production-grade authentication.
- Firmware uses open CORS (`*`) for local LAN tooling only; do not expose the ESP32 HTTP server to the public internet without authentication.
