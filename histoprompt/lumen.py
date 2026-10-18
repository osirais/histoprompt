from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from .config import Settings


class LumenError(RuntimeError):
    pass


class LumenClient:
    def __init__(self, settings: Settings):
        self.api_key = settings.lumen_api_key
        self.base_url = settings.lumen_base_url
        self.default_model = settings.lumen_model

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _request(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        if not self.api_key:
            raise LumenError("LUMEN_API_KEY is not configured.")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST" if payload is not None else "GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=int(os.getenv("LUMEN_TIMEOUT", "120"))) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise LumenError(f"Lumen returned HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise LumenError(f"Could not reach Lumen: {exc}") from exc

    def list_models(self) -> list[str]:
        if not self.configured:
            return []
        response = self._request("/models")
        return sorted(
            str(item["id"])
            for item in response.get("data", [])
            if isinstance(item, dict) and item.get("id")
        )

    def complete(self, system: str, prompt: str, model: str = "") -> tuple[str, str]:
        selected_model = model or self.default_model
        if not selected_model:
            models = self.list_models()
            if not models:
                raise LumenError(
                    "No acknowledged Lumen chat model is available. Select one on the Lumen model dashboard."
                )
            selected_model = models[0]
        response = self._request(
            "/chat/completions",
            {
                "model": selected_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": int(os.getenv("LUMEN_MAX_TOKENS", "1400")),
            },
        )
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LumenError("Lumen returned an unexpected chat response.") from exc
        if not isinstance(content, str) or not content.strip():
            raise LumenError(
                f"Lumen model {selected_model} completed without a text response. "
                "Choose a non-reasoning chat model or raise its output-token limit."
            )
        return str(content), selected_model

