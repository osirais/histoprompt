from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import ROOT, Settings
from .conch_backend import ConchError
from .demo_replay import demo_case_payload, demo_model_statuses, load_demo_fixture
from .hosted_backend import HostedModelError, hosted_model_status
from .lumen import LumenError
from .musk_backend import MuskError, musk_status
from .pipeline import AnalysisPipeline


WEB_ROOT = ROOT / "web"
MAX_REQUEST_BYTES = 35 * 1024 * 1024


class HistoPromptServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], settings: Settings):
        super().__init__(address, HistoPromptHandler)
        self.settings = settings
        if settings.demo_replay:
            load_demo_fixture(settings.demo_replay_path)
        self.pipeline = AnalysisPipeline.create(settings)


class HistoPromptHandler(BaseHTTPRequestHandler):
    server: HistoPromptServer

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
            demo_replay = self.server.settings.demo_replay
            model_statuses = (
                demo_model_statuses()
                if demo_replay
                else {
                    "musk": musk_status(self.server.settings),
                    "conch": hosted_model_status(self.server.settings, "conch"),
                    "quiltnet": hosted_model_status(self.server.settings, "quiltnet"),
                    "plip": hosted_model_status(self.server.settings, "plip"),
                }
            )
            self._json(
                {
                    "demo_replay": demo_replay,
                    "models": model_statuses,
                    "musk": model_statuses["musk"],
                    "conch": model_statuses["conch"],
                    "lumen": {
                        "configured": True if demo_replay else lumen.configured,
                        "detail": (
                            "Saved Lumen review"
                            if demo_replay
                            else self.server.settings.lumen_base_url
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
        if path == "/api/demo-case":
            try:
                self._json(demo_case_payload(self.server.settings.demo_replay_path))
            except ValueError as exc:
                self._json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        if path == "/api/models":
            if self.server.settings.demo_replay:
                self._json({"models": ["saved-demo-replay"], "default": "saved-demo-replay"})
                return
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
        except (ConchError, HostedModelError, MuskError, LumenError) as exc:
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
    server = HistoPromptServer((settings.host, settings.port), settings)
    print(f"HistoPrompt is running at http://{settings.host}:{settings.port}")
    if settings.demo_replay:
        print("Saved demo replay is active; no remote model or Lumen requests will be made.")
    print("Research prototype only; do not use for patient care.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

