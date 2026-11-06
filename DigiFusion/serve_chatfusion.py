#!/usr/bin/env python3
"""
Proxy GET /chat-token → POST API_ENDPOINT (embed-sessions).
Konfigurasi: DigiFusion/.env — API_TOKEN, API_ENDPOINT (lihat .env.example).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TESTING_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = Path(__file__).resolve().parent / ".env"

ENV_KEYS = ("API_TOKEN", "API_ENDPOINT")

CHAT_PAGE = "/DigiFusion/ChatFusion1.html"


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    for key in ENV_KEYS:
        val = os.environ.get(key, "").strip()
        if val:
            out[key] = val

    if not ENV_FILE.is_file():
        return out

    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, raw = line.partition("=")
        key = key.strip()
        if key not in ENV_KEYS or key in out:
            continue
        out[key] = raw.strip().strip("'\"")
    return out


def embed_sessions_url(api_endpoint: str) -> str:
    """Terima URL penuh embed-sessions atau .../chat dari DigiFusion."""
    url = api_endpoint.strip().rstrip("/")
    if url.endswith("/chat"):
        return url[: -len("/chat")] + "/embed-sessions"
    return url


class ChatFusionHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(TESTING_ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/chat-token":
            self._handle_chat_token()
            return
        if path == "/":
            self.send_response(302)
            self.send_header("Location", CHAT_PAGE)
            self.end_headers()
            return
        if path in ("/ChatFusion1.html", "/ChatFusion1.html/"):
            self.send_response(302)
            self.send_header("Location", "/DigiFusion/ChatFusion1.html")
            self.end_headers()
            return
        super().do_GET()

    def _handle_chat_token(self) -> None:
        cfg = load_env()
        api_token = cfg.get("API_TOKEN", "")
        api_endpoint = cfg.get("API_ENDPOINT", "")

        if not api_token or not api_endpoint:
            self.send_error(
                500,
                "Set API_TOKEN and API_ENDPOINT in env or DigiFusion/.env — see .env.example",
            )
            return

        post_url = embed_sessions_url(api_endpoint)

        body = json.dumps(
            {
                "user": {
                    "email": "gabonleon@localhost",
                    "name": "Bang Gabon",
                },
                "access": {
                    "level": "admin",
                    "scope": [],
                },
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            post_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": api_token,
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = resp.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            self.send_error(exc.code, f"embed-sessions failed: {detail}")
            return
        except OSError as exc:
            self.send_error(502, f"embed-sessions request failed: {exc}")
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args) -> None:
        if args and isinstance(args[0], str) and "/chat-token" in args[0]:
            return
        super().log_message(fmt, *args)


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("", port), ChatFusionHandler)
    print(f"Serving {TESTING_ROOT} at http://localhost:{port}/")
    print(f"Normal iframe: http://localhost:{port}/DigiFusion/ChatFusion1.html")
    print(f"Mini widget:   http://localhost:{port}/DigiFusion/ChatFusionWidget.html")
    print("Token API: DigiFusion/.env (API_TOKEN, API_ENDPOINT)")
    server.serve_forever()


if __name__ == "__main__":
    main()
