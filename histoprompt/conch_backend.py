from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any

from .config import Settings
from .musk_backend import Prediction, decode_image


class ConchError(RuntimeError):
    """An unavailable or malformed NCSA CONCH response."""


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> Any:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:800]
        raise ConchError(f"CONCH endpoint returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ConchError(f"Could not reach the CONCH endpoint: {exc}") from exc


class RemoteConch:
    """Adapter for the hackathon's NCSA-hosted CONCH service."""

    def __init__(self, settings: Settings):
        if not settings.conch_endpoint:
            raise ConchError(
                "CONCH_ENDPOINT is required when CONCH_BACKEND=remote."
            )
        if not settings.conch_api_key:
            raise ConchError("CONCH_API_KEY is required when CONCH_BACKEND=remote.")
        self.endpoint = settings.conch_endpoint.rstrip("/")
        self.api_key = settings.conch_api_key

    def classify(
        self, image_data_url: str, prompts: dict[str, str]
    ) -> list[Prediction]:
        endpoint = self.endpoint
        if not endpoint.endswith("/classify"):
            endpoint += "/classify"
        image = decode_image(image_data_url)
        response = _post_json(
            endpoint,
            {
                "images": [base64.b64encode(image).decode("ascii")],
                "prompts": prompts,
            },
            {"Authorization": f"Bearer {self.api_key}"},
        )
        values = response.get("results") if isinstance(response, dict) else None
        if not isinstance(values, list) or len(values) != 1:
            raise ConchError("CONCH endpoint did not return one result for the image.")
        try:
            item = values[0]
            return [Prediction(str(item["predicted_label"]), float(item["score"]))]
        except (KeyError, TypeError, ValueError) as exc:
            raise ConchError(
                "Each CONCH result must contain predicted_label and score fields."
            ) from exc


def make_conch_backend(settings: Settings) -> RemoteConch:
    if settings.conch_backend == "remote":
        return RemoteConch(settings)
    raise ConchError("CONCH_BACKEND must be either remote or disabled.")


def conch_status(settings: Settings) -> dict[str, Any]:
    if settings.conch_backend != "remote":
        return {"configured": False, "backend": "disabled", "detail": "CONCH is disabled"}
    if not settings.conch_endpoint or not settings.conch_api_key:
        return {
            "configured": False,
            "backend": "remote",
            "detail": "CONCH_ENDPOINT and CONCH_API_KEY are required",
        }
    health_url = settings.conch_endpoint.rstrip("/")
    if health_url.endswith("/classify"):
        health_url = health_url[: -len("/classify")]
    try:
        request = urllib.request.Request(f"{health_url}/health", method="GET")
        with urllib.request.urlopen(request, timeout=2) as response:
            health = json.loads(response.read().decode("utf-8"))
        model_name = str(health.get("model", "CONCH"))
        return {
            "configured": health.get("status") == "ok",
            "backend": "remote",
            "detail": f"NCSA-hosted {model_name}",
        }
    except Exception:
        return {
            "configured": False,
            "backend": "remote",
            "detail": "CONCH tunnel is not connected",
        }
