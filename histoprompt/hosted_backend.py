from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from typing import Any

from .config import Settings
from .musk_backend import Prediction, decode_image, make_musk_backend


MODEL_NAMES = {
    "musk": "MUSK",
    "conch": "CONCH",
    "quiltnet": "QuiltNet-B-32",
    "plip": "PLIP",
}


def _endpoint_credentials(settings: Settings, model: str) -> tuple[str, str]:
    if model == "conch":
        return settings.conch_endpoint, settings.conch_api_key
    if model == "quiltnet":
        return (
            getattr(settings, "quiltnet_endpoint", os.getenv("QUILTNET_ENDPOINT", "")),
            getattr(settings, "quiltnet_api_key", os.getenv("QUILTNET_API_KEY", "")),
        )
    if model == "plip":
        return (
            getattr(settings, "plip_endpoint", os.getenv("PLIP_ENDPOINT", "")),
            getattr(settings, "plip_api_key", os.getenv("PLIP_API_KEY", "")),
        )
    raise HostedModelError(f"Unknown hosted model: {model}")


class HostedModelError(RuntimeError):
    """An unavailable or malformed hosted pathology-model response."""


def _post_json(
    model_name: str, url: str, payload: dict[str, Any], headers: dict[str, str]
) -> Any:
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
        raise HostedModelError(
            f"{model_name} endpoint returned HTTP {exc.code}: {detail}"
        ) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise HostedModelError(f"Could not reach the {model_name} endpoint: {exc}") from exc


class RemoteHostedModel:
    """Adapter for the shared NCSA /classify contract used by hosted models."""

    def __init__(self, model_name: str, endpoint: str, api_key: str):
        if not endpoint:
            raise HostedModelError(f"{model_name} endpoint is required.")
        if not api_key:
            raise HostedModelError(f"{model_name} API key is required.")
        self.model_name = model_name
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key

    def classify(
        self, image_data_url: str, prompts: dict[str, str]
    ) -> list[Prediction]:
        return self.classify_batch([image_data_url], prompts)

    def classify_batch(
        self, image_data_urls: list[str], prompts: dict[str, str]
    ) -> list[Prediction]:
        if not image_data_urls:
            return []
        endpoint = self.endpoint
        if not endpoint.endswith("/classify"):
            endpoint += "/classify"
        images = [
            base64.b64encode(decode_image(image_data_url)).decode("ascii")
            for image_data_url in image_data_urls
        ]
        response = _post_json(
            self.model_name,
            endpoint,
            {"images": images, "prompts": prompts},
            {"Authorization": f"Bearer {self.api_key}"},
        )
        values = response.get("results") if isinstance(response, dict) else None
        if not isinstance(values, list) or len(values) != len(images):
            count = len(values) if isinstance(values, list) else 0
            raise HostedModelError(
                f"{self.model_name} returned {count} results for {len(images)} images."
            )
        try:
            return [
                Prediction(str(item["predicted_label"]), float(item["score"]))
                for item in values
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise HostedModelError(
                f"Each {self.model_name} result must contain predicted_label and score fields."
            ) from exc


def make_benchmark_backend(settings: Settings, model: str) -> Any:
    """Build one benchmark backend without placing credentials in result files."""
    if model == "musk":
        return make_musk_backend(settings)
    endpoint, api_key = _endpoint_credentials(settings, model)
    return RemoteHostedModel(MODEL_NAMES[model], endpoint, api_key)


def hosted_model_status(settings: Settings, model: str) -> dict[str, Any]:
    """Return a small, credential-free health summary for an optional model."""
    endpoint, api_key = _endpoint_credentials(settings, model)
    if not endpoint or not api_key:
        return {
            "configured": False,
            "backend": "remote",
            "detail": f"{MODEL_NAMES[model]} is not configured",
        }
    health_url = endpoint.rstrip("/")
    if health_url.endswith("/classify"):
        health_url = health_url[: -len("/classify")]
    try:
        request = urllib.request.Request(
            f"{health_url}/health",
            headers={"Authorization": f"Bearer {api_key}"},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            health = json.loads(response.read().decode("utf-8"))
        return {
            "configured": health.get("status") == "ok",
            "backend": "remote",
            "detail": f"NCSA-hosted {health.get('model', MODEL_NAMES[model])}",
        }
    except Exception:
        return {
            "configured": False,
            "backend": "remote",
            "detail": f"{MODEL_NAMES[model]} tunnel is not connected",
        }
