#!/usr/bin/env python3
"""
Proxy GET /chat-token → embed-sessions (API key dari env atau .env).
Sesuaikan AGENT_ID + API_BASE dengan snippet Agents → API (sama seperti HTML).
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

# Salin dari Agents → API (iframe / widget) bila ganti agent
API_BASE = "https://ppn-rag-console-fe-dev-431311422997.asia-southeast2.run.app"
AGENT_ID = "d0a88d7d-ea2b-4dc7-9ae2-19caf7dc070a"

CHAT_PAGE = "/DigiFusion/ChatFusion1.html"


def load_api_key() -> str:
    key = os.environ.get("CHATFUSION_API_KEY", "").strip()
    if key:
        return key
    if not ENV_FILE.is_file():
        return ""
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("CHATFUSION_API_KEY="):
            return line.split("=", 1)[1].strip().strip("'\"")
    return ""


def embed_sessions_url() -> str:
    base = API_BASE.rstrip("/")
    return f"{base}/api/v1/agents/{AGENT_ID}/embed-sessions"


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
        api_key = load_api_key()
        if not api_key:
            self.send_error(
                500,
                "Set CHATFUSION_API_KEY (export) or DigiFusion/.env — see .env.example",
            )
            return

        body = json.dumps(
            {
                "user": {
                    "email": "embed-demo@localhost",
                    "name": "Embed Demo",
                },
                "access": {
                    "level": "admin",
                    "scope": [],
                },
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            embed_sessions_url(),
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": api_key,
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
    print("Token API: DigiFusion/.env (CHATFUSION_API_KEY=xxxxx)")
    server.serve_forever()


if __name__ == "__main__":
    main()
