import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

os.environ.setdefault("FORWARDED_ALLOW_IPS", "*")

from mcp.server.fastmcp import FastMCP
import requests
import socket
from datetime import datetime
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import RedirectResponse, JSONResponse
from starlette.requests import Request

import uvicorn

# Configuration from environment (see .env.example)
ESP32_IP = os.environ.get("ESP32_IP", "192.168.1.100")
ESP32_TIMEOUT = int(os.environ.get("ESP32_TIMEOUT", "5"))
NGROK_URL = os.environ.get("NGROK_URL", "").rstrip("/")
OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "claude_client")
OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET", "change-me")
OAUTH_ACCESS_TOKEN = os.environ.get("OAUTH_ACCESS_TOKEN", "change-me")

# ==================================================
# MCP SERVER
# ==================================================
mcp = FastMCP(
    name="esp32_mcp",
    instructions="""
    This server controls an ESP32 board over HTTP.
    Available tools: led_on, led_off, led_status, ping_esp32, get_esp32_ip
    """,
)

# ==================================================
# HELPERS
# ==================================================
def log(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "Unknown"


def call_esp32(endpoint: str):
    try:
        url = f"http://{ESP32_IP}{endpoint}"
        log(f"Calling: {url}")
        response = requests.get(url, timeout=ESP32_TIMEOUT)
        response.raise_for_status()
        log(f"ESP32 Response: {response.text}")
        return response.text
    except Exception as e:
        log(f"ERROR: {e}")
        return f"ERROR: {str(e)}"


# ==================================================
# MCP TOOLS
# ==================================================
@mcp.tool()
def led_on() -> str:
    """Turn the ESP32 onboard LED ON."""
    return call_esp32("/led/on")


@mcp.tool()
def led_off() -> str:
    """Turn the ESP32 onboard LED OFF."""
    return call_esp32("/led/off")


@mcp.tool()
def led_status() -> str:
    """Get current LED status."""
    return call_esp32("/led/status")


@mcp.tool()
def ping_esp32() -> dict:
    """Check whether the ESP32 is reachable."""
    try:
        response = requests.get(f"http://{ESP32_IP}/led/status", timeout=3)
        return {"reachable": True, "status": response.text, "ip": ESP32_IP}
    except Exception as e:
        return {"reachable": False, "error": str(e), "ip": ESP32_IP}


@mcp.tool()
def get_esp32_ip() -> str:
    """Return the configured ESP32 IP address."""
    return ESP32_IP


# ==================================================
# HOST HEADER FIX — strips ngrok host so MCP accepts it
# ==================================================
class FixHostMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            scope["headers"] = [
                (k, v) for k, v in scope.get("headers", []) if k.lower() != b"host"
            ] + [(b"host", b"localhost:8000")]
        await self.app(scope, receive, send)


# ==================================================
# OAUTH ENDPOINTS — Claude.ai needs these to connect
# ==================================================
def _public_base_url() -> str:
    if NGROK_URL:
        return NGROK_URL
    return "http://127.0.0.1:8000"


async def oauth_metadata(request: Request):
    base = _public_base_url()
    return JSONResponse(
        {
            "issuer": base,
            "authorization_endpoint": f"{base}/oauth/authorize",
            "token_endpoint": f"{base}/oauth/token",
            "registration_endpoint": f"{base}/oauth/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256"],
        }
    )


async def oauth_register(request: Request):
    body = await request.json()
    return JSONResponse(
        {
            "client_id": OAUTH_CLIENT_ID,
            "client_secret": OAUTH_CLIENT_SECRET,
            "client_name": body.get("client_name", "Claude"),
            "redirect_uris": body.get("redirect_uris", []),
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "client_secret_post",
        }
    )


async def oauth_authorize(request: Request):
    redirect_uri = request.query_params.get("redirect_uri", "")
    state = request.query_params.get("state", "")
    return RedirectResponse(url=f"{redirect_uri}?code=esp32_noauth&state={state}")


async def oauth_token(request: Request):
    return JSONResponse(
        {
            "access_token": OAUTH_ACCESS_TOKEN,
            "token_type": "bearer",
            "expires_in": 999999,
            "scope": "mcp",
        }
    )


# ==================================================
# STARTUP
# ==================================================
if __name__ == "__main__":
    claude_url = f"{_public_base_url()}/sse" if NGROK_URL else "http://127.0.0.1:8000/sse"
    print("=" * 55)
    print("         ESP32 MCP SERVER")
    print("=" * 55)
    print(f"PC IP         : {get_local_ip()}")
    print(f"ESP32 IP      : {ESP32_IP}")
    print(f"ngrok URL     : {NGROK_URL or '(not set — local only)'}")
    print(f"Claude.ai URL : {claude_url}")
    print("=" * 55)

    mcp_app = mcp.sse_app()

    app = Starlette(
        routes=[
            Route("/.well-known/oauth-authorization-server", oauth_metadata),
            Route("/oauth/register", oauth_register, methods=["POST"]),
            Route("/oauth/authorize", oauth_authorize),
            Route("/oauth/token", oauth_token, methods=["GET", "POST"]),
            Mount("/", app=mcp_app),
        ]
    )

    app.add_middleware(FixHostMiddleware)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
