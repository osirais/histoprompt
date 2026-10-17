from __future__ import annotations

import base64
import io
import json
import os
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Settings


class MuskError(RuntimeError):
    pass


@dataclass(frozen=True)
class Prediction:
    label: str
    probability: float

    def as_dict(self) -> dict[str, str | float]:
        return {"label": self.label, "probability": round(self.probability, 6)}


def decode_image(data_url: str, max_bytes: int = 25 * 1024 * 1024) -> bytes:
    encoded = data_url.split(",", 1)[1] if "," in data_url else data_url
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise MuskError("The uploaded image is not valid base64 data.") from exc
    if not raw:
        raise MuskError("The uploaded image is empty.")
    if len(raw) > max_bytes:
        raise MuskError("The uploaded image is larger than 25 MB.")
    return raw


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
        raise MuskError(f"MUSK endpoint returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise MuskError(f"Could not reach the MUSK endpoint: {exc}") from exc


class RemoteMusk:
    """Adapter for the hackathon's NCSA-hosted pathology model service."""

    def __init__(self, settings: Settings):
        if not settings.musk_endpoint:
            raise MuskError("MUSK_ENDPOINT is required when MUSK_BACKEND=remote.")
        self.endpoint = settings.musk_endpoint.rstrip("/")
        self.api_key = settings.musk_api_key

    def classify(
        self, image_data_url: str, prompts: dict[str, str]
    ) -> list[Prediction]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        endpoint = self.endpoint
        if not endpoint.endswith("/classify"):
            endpoint += "/classify"
        image_b64 = base64.b64encode(decode_image(image_data_url)).decode("ascii")
        response = _post_json(
            endpoint,
            {
                "images": [image_b64],
                "prompts": prompts,
            },
            headers,
        )
        values = response.get("results") if isinstance(response, dict) else None
        if not isinstance(values, list) or not values:
            raise MuskError("MUSK endpoint did not return a results array.")
        try:
            predictions = [
                Prediction(str(item["predicted_label"]), float(item["score"]))
                for item in values
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise MuskError(
                "Each MUSK result must contain predicted_label and score fields."
            ) from exc
        return sorted(predictions, key=lambda item: item.probability, reverse=True)


class LocalMusk:
    """Lazy singleton around the official lilab-stanford/MUSK implementation."""

    _lock = threading.Lock()
    _loaded: tuple[Any, Any, Any, Any, Any] | None = None

    def __init__(self, settings: Settings):
        self.requested_device = settings.musk_device

    def _load(self) -> tuple[Any, Any, Any, Any, Any]:
        with self._lock:
            if self.__class__._loaded is not None:
                return self.__class__._loaded
            try:
                import torch
                import torchvision
                from huggingface_hub import hf_hub_download
                from PIL import Image
                from timm.data.constants import IMAGENET_INCEPTION_MEAN, IMAGENET_INCEPTION_STD
                from timm.models import create_model
                from transformers import XLMRobertaTokenizer
                import musk
                from musk import modeling, utils  # noqa: F401 - registers the timm model
            except ImportError as exc:
                raise MuskError(
                    "Official MUSK dependencies are missing. Install the GPU environment "
                    "with `uv sync --extra musk` on the NCSA host."
                ) from exc

            requested_device = self.requested_device
            if requested_device == "auto":
                if torch.cuda.is_available():
                    requested_device = "cuda"
                elif torch.backends.mps.is_available():
                    requested_device = "mps"
                else:
                    requested_device = "cpu"
            if requested_device == "cuda" and not torch.cuda.is_available():
                raise MuskError(
                    "MUSK_DEVICE=cuda, but CUDA is unavailable. Run this on the NCSA GPU host "
                    "or explicitly select cpu for a slow smoke test."
                )
            if requested_device == "mps" and not torch.backends.mps.is_available():
                raise MuskError(
                    "MUSK_DEVICE=mps, but Apple Metal acceleration is unavailable. "
                    "Use auto, cpu, or run on a supported Apple Silicon Mac."
                )
            device = torch.device(requested_device)
            dtype = torch.float16 if device.type == "cuda" else torch.float32
            try:
                model = create_model("musk_large_patch16_384").eval()
                utils.load_model_and_may_interpolate(
                    "hf_hub:xiangjx/musk", model, "model|module", ""
                )
                model.to(device=device, dtype=dtype).eval()
                tokenizer_path = Path(musk.__file__).resolve().parent / "models" / "tokenizer.spm"
                if not tokenizer_path.exists():
                    tokenizer_path = Path(
                        hf_hub_download(repo_id="xiangjx/musk", filename="tokenizer.spm")
                    )
                tokenizer = XLMRobertaTokenizer(str(tokenizer_path))
                transform = torchvision.transforms.Compose(
                    [
                        torchvision.transforms.Resize(384, interpolation=3, antialias=True),
                        torchvision.transforms.CenterCrop((384, 384)),
                        torchvision.transforms.ToTensor(),
                        torchvision.transforms.Normalize(
                            mean=IMAGENET_INCEPTION_MEAN,
                            std=IMAGENET_INCEPTION_STD,
                        ),
                    ]
                )
            except Exception as exc:
                hint = " Verify HF_TOKEN and accept the xiangjx/musk model terms."
                raise MuskError(f"Could not load the official MUSK weights.{hint} {exc}") from exc
            self.__class__._loaded = (torch, Image, model, tokenizer, (transform, utils, device, dtype))
            return self.__class__._loaded

    def classify(
        self, image_data_url: str, prompts: dict[str, str]
    ) -> list[Prediction]:
        torch, Image, model, tokenizer, helpers = self._load()
        transform, utils, device, dtype = helpers
        labels = list(prompts)
        try:
            image = Image.open(io.BytesIO(decode_image(image_data_url))).convert("RGB")
        except Exception as exc:
            raise MuskError(f"Could not decode the uploaded pathology image: {exc}") from exc
        image_tensor = transform(image).unsqueeze(0).to(device=device, dtype=dtype)
        text_ids = []
        paddings = []
        for label, description in prompts.items():
            ids, padding = utils.xlm_tokenizer(
                description, tokenizer, max_len=100
            )
            text_ids.append(torch.tensor(ids).unsqueeze(0))
            paddings.append(torch.tensor(padding).unsqueeze(0))
        text_tensor = torch.cat(text_ids).to(device)
        padding_tensor = torch.cat(paddings).to(device)
        with torch.inference_mode():
            image_embedding = model(
                image=image_tensor,
                with_head=True,
                out_norm=True,
            )[0]
            text_embedding = model(
                text_description=text_tensor,
                padding_mask=padding_tensor,
                with_head=True,
                out_norm=True,
            )[1]
            probabilities = (
                model.logit_scale * image_embedding @ text_embedding.T
            ).softmax(dim=-1)[0]
        values = probabilities.detach().float().cpu().tolist()
        return sorted(
            [Prediction(label, probability) for label, probability in zip(labels, values)],
            key=lambda item: item.probability,
            reverse=True,
        )


def make_musk_backend(settings: Settings) -> LocalMusk | RemoteMusk:
    if settings.musk_backend == "local":
        return LocalMusk(settings)
    if settings.musk_backend == "remote":
        return RemoteMusk(settings)
    raise MuskError("MUSK_BACKEND must be either local or remote.")


def musk_status(settings: Settings) -> dict[str, Any]:
    if settings.musk_backend == "remote":
        if not settings.musk_endpoint:
            return {
                "configured": False,
                "backend": "remote",
                "detail": "MUSK_ENDPOINT is missing",
            }
        health_url = settings.musk_endpoint.rstrip("/")
        if health_url.endswith("/classify"):
            health_url = health_url[: -len("/classify")]
        try:
            request = urllib.request.Request(f"{health_url}/health", method="GET")
            with urllib.request.urlopen(request, timeout=2) as response:
                health = json.loads(response.read().decode("utf-8"))
            model_name = str(health.get("model", "unknown"))
            return {
                "configured": health.get("status") == "ok",
                "backend": "remote",
                "detail": f"NCSA-hosted {model_name}",
            }
        except Exception:
            return {
                "configured": False,
                "backend": "remote",
                "detail": "Delta tunnel is not connected",
            }
    cached_token_paths = (
        Path.home() / ".cache" / "huggingface" / "token",
        Path.home() / ".huggingface" / "token",
    )
    has_hf_token = bool(
        os.getenv("HF_TOKEN")
        or os.getenv("HUGGING_FACE_HUB_TOKEN")
        or any(path.exists() and path.stat().st_size > 0 for path in cached_token_paths)
    )
    try:
        import importlib.util

        dependencies = all(
            importlib.util.find_spec(name) is not None
            for name in ("torch", "torchvision", "timm", "transformers", "musk")
        )
    except (ImportError, ValueError):
        dependencies = False
    return {
        "configured": dependencies and has_hf_token,
        "backend": "local",
        "detail": (
            f"Official weights on {settings.musk_device}"
            if dependencies and has_hf_token
            else "Needs MUSK dependencies and HF_TOKEN"
        ),
    }

