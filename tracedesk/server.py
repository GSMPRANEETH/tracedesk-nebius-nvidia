"""Loopback-only TraceDesk demo. Run: python3 -m tracedesk.server."""

import argparse
import getpass
import json
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .core import Store, answer, load_runbook

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
TOKEN = secrets.token_urlsafe(32)


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, *_):
        pass  # Questions and corrections never enter access logs.

    def send(self, status, data, content_type="application/json; charset=utf-8"):
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def allowed_host(self):
        return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

    def do_GET(self):
        if not self.allowed_host():
            return self.send(403, {"error": "Use the printed 127.0.0.1 address."})
        path = urlsplit(self.path).path
        if path == "/api/context":
            return self.send(200, {"sources": load_runbook(), "csrf_token": TOKEN,
                "configured": bool(os.environ.get("NEBIUS_API_KEY", "").strip()),
                "model": os.environ.get("NEBIUS_MODEL", "nvidia/Nemotron-3_5-Lightning"),
                "provider": "Nebius Token Factory", "mode": "local-single-operator"})
        if path == "/api/corrections":
            all_sources = load_runbook()
            scopes = {(x["product"], x["version"]) for x in all_sources}
            return self.send(200, {"corrections": [c for p, v in sorted(scopes) for c in self.server.store.list(p, v)]})
        assets = {"/": ("index.html", "text/html; charset=utf-8"),
                  "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                  "/style.css": ("style.css", "text/css; charset=utf-8")}
        if path in assets:
            name, mime = assets[path]
            return self.send(200, (WEB / name).read_bytes(), mime)
        return self.send(404, {"error": "Not found"})

    def do_POST(self):
        expected = f"http://127.0.0.1:{self.server.server_port}"
        if not self.allowed_host() or self.headers.get("Origin") != expected or not secrets.compare_digest(self.headers.get("X-TraceDesk-Token", ""), TOKEN):
            return self.send(403, {"error": "Request origin or token is invalid. Reload the app."})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send(415, {"error": "Expected JSON."})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 12288:
                return self.send(413, {"error": "Request must contain at most 12 KB."})
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError("Expected a JSON object.")
            path = urlsplit(self.path).path
            if path == "/api/answer":
                if type(body.get("use_memory", True)) is not bool:
                    raise ValueError("Memory selection must be true or false.")
                if not self.server.inference_lock.acquire(blocking=False):
                    return self.send(429, {"error": "An inference request is already running. Wait for it to finish."})
                try:
                    corrections = self.server.store.list(body.get("product", ""), body.get("version", ""))
                    result = answer(body.get("question", ""), body.get("product", ""), body.get("version", ""), corrections, body.get("use_memory", True))
                finally:
                    self.server.inference_lock.release()
                return self.send(200, result)
            if path == "/api/corrections":
                saved = self.server.store.save(body.get("product", ""), body.get("version", ""), body.get("question", ""), body.get("text", ""), body.get("evidence_ids", []), body.get("approved", False))
                return self.send(200, {"correction": saved})
            if path == "/api/clear":
                self.server.store.clear()
                return self.send(200, {"cleared": True})
            return self.send(404, {"error": "Not found"})
        except (ValueError, TypeError, UnicodeError) as exc:
            return self.send(400, {"error": str(exc)[:240]})
        except RuntimeError as exc:
            # Core errors are sanitized at the provider boundary; preserve the actual recovery reason.
            return self.send(503, {"error": f"{exc} No generated answer was substituted."})
        except Exception:
            return self.send(500, {"error": "The request failed. Your saved evidence has not been replaced."})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", type=Path, default=ROOT / ".local" / "corrections.sqlite3")
    parser.add_argument("--prompt-key", action="store_true", help="Read a Nebius key privately for this process only")
    args = parser.parse_args()
    if args.prompt_key:
        key = getpass.getpass("Nebius API key (not saved): ").strip()
        if not key:
            parser.error("A nonempty API key is required when using --prompt-key")
        os.environ["NEBIUS_API_KEY"] = key
    args.db.parent.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.store = Store(args.db)
    # Ponytail: serialize paid calls for this single-operator demo; use authenticated quotas for a hosted service.
    server.inference_lock = threading.Lock()
    print(f"TraceDesk: http://127.0.0.1:{server.server_port}", flush=True)
    print("Single-operator local workspace. Ctrl+C to stop. No external bind is supported.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
