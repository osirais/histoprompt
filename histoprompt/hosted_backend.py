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
    if model == "conch":
        endpoint = settings.conch_endpoint
        api_key = settings.conch_api_key
    elif model == "quiltnet":
        endpoint = os.getenv("QUILTNET_ENDPOINT", "")
        api_key = os.getenv("QUILTNET_API_KEY", "")
    elif model == "plip":
        endpoint = os.getenv("PLIP_ENDPOINT", "")
        api_key = os.getenv("PLIP_API_KEY", "")
    else:
        raise HostedModelError(f"Unknown benchmark model: {model}")
    return RemoteHostedModel(MODEL_NAMES[model], endpoint, api_key)
