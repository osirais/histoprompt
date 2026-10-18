"""Classifier backends for the multitask scripts.

MUSK goes through histoprompt.musk_backend. CONCH, QuiltNet-B-32 and PLIP go through the shared NCSA /classify
endpoint (POST {"images": [base64], "prompts": {label: text}} -> {"results": [{"predicted_label", "score"}]}), with
the same environment variables as histoprompt/hosted_backend.py on main: CONCH_ENDPOINT / CONCH_API_KEY,
QUILTNET_ENDPOINT / QUILTNET_API_KEY, PLIP_ENDPOINT / PLIP_API_KEY (read from .env.local).
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from histoprompt.config import Settings
from histoprompt.musk_backend import make_musk_backend

MODELS = {"musk": "MUSK", "conch": "CONCH", "quiltnet": "QuiltNet-B-32", "plip": "PLIP"}
DEFAULT_ENDPOINTS = {"conch": "http://127.0.0.1:8802", "quiltnet": "http://127.0.0.1:8803", "plip": "http://127.0.0.1:8804"}


@dataclass
class Prediction:
    label: str
    score: float


class HostedModel:
    def __init__(self, model: str):
        self.name = MODELS[model]
        self.endpoint = os.getenv(f"{model.upper()}_ENDPOINT", DEFAULT_ENDPOINTS[model]).rstrip("/")
        if not self.endpoint.endswith("/classify"):
            self.endpoint += "/classify"
        self.api_key = os.getenv(f"{model.upper()}_API_KEY", "")
        if not self.api_key:
            raise SystemExit(f"{model.upper()}_API_KEY is not set (add it to .env.local).")

    def classify_batch(self, image_data_urls: list[str], prompts: dict[str, str]) -> list[Prediction]:
        images = [u.split(",", 1)[1] for u in image_data_urls]
        request = urllib.request.Request(
            self.endpoint, data=json.dumps({"images": images, "prompts": prompts}).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=int(os.getenv("HOSTED_TIMEOUT", "300"))) as response:
                results = json.loads(response.read())["results"]
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"{self.name} returned HTTP {exc.code}: {exc.read()[:500]!r}") from exc
        if len(results) != len(images):
            raise RuntimeError(f"{self.name} returned {len(results)} results for {len(images)} images.")
        return [Prediction(str(r["predicted_label"]), float(r["score"])) for r in results]


def make_backend(model: str):
    settings = Settings.from_env()          # also loads .env.local into the environment
    if model == "musk":
        return make_musk_backend(settings)
    return HostedModel(model)


def output_name(stem: str, model: str) -> str:
    """results.json for MUSK (the committed runs), results_<model>.json for the others."""
    return f"{stem}.json" if model == "musk" else f"{stem}_{model}.json"
