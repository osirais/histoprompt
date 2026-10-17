from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import ROOT, Settings
from .lumen import LumenError
from .musk_backend import MuskError, musk_status
from .pipeline import AnalysisPipeline


WEB_ROOT = ROOT / "web"
MAX_REQUEST_BYTES = 35 * 1024 * 1024


class AshbyServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], settings: Settings):
        super().__init__(address, AshbyHandler)
        self.settings = settings
        self.pipeline = AnalysisPipeline.create(settings)


class AshbyHandler(BaseHTTPRequestHandler):
    server: AshbyServer

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")

    def _json(self, payload: Any, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/status":
            lumen = self.server.pipeline.lumen
            self._json(
                {
                    "musk": musk_status(self.server.settings),
                    "lumen": {
                        "configured": lumen.configured,
                        "detail": (
                            self.server.settings.lumen_base_url
                            if lumen.configured
                            else "Needs LUMEN_API_KEY"
                        ),
                    },
                    "corpus": {
                        "configured": True,
                        "documents": len(self.server.pipeline.evidence_index.documents),
                        "detail": str(self.server.settings.corpus_path),
                    },
                }
            )
            return
        if path == "/api/models":
            try:
                self._json(
                    {
                        "models": self.server.pipeline.lumen.list_models(),
                        "default": self.server.settings.lumen_model,
                    }
                )
            except LumenError as exc:
                self._json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return
        self._serve_static(path)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/analyze":
            self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_REQUEST_BYTES:
                raise ValueError("Request must be between 1 byte and 35 MB.")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object.")
            self._json(self.server.pipeline.analyze(payload))
        except (ValueError, json.JSONDecodeError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except (MuskError, LumenError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
        except Exception as exc:
            self._json({"error": f"Unexpected server error: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _serve_static(self, request_path: str) -> None:
        relative = "index.html" if request_path in ("", "/") else request_path.lstrip("/")
        candidate = (WEB_ROOT / relative).resolve()
        if WEB_ROOT.resolve() not in candidate.parents and candidate != WEB_ROOT.resolve():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not candidate.is_file():
            candidate = WEB_ROOT / "index.html"
        body = candidate.read_bytes()
        mime_type, _ = mimetypes.guess_type(candidate.name)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{mime_type or 'application/octet-stream'}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    settings = Settings.from_env()
    server = AshbyServer((settings.host, settings.port), settings)
    print(f"Ashby is running at http://{settings.host}:{settings.port}")
    print("Research prototype only; do not use for patient care.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

