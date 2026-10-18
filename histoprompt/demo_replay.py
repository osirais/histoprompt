from __future__ import annotations

import base64
import copy
import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Any

from .config import ROOT


DEMO_MODELS = {
    "musk": "MUSK",
    "conch": "CONCH",
    "quiltnet": "QuiltNet-B-32",
    "plip": "PLIP",
}


def load_demo_fixture(path: Path) -> dict[str, Any]:
    try:
        fixture = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Saved demo fixture was not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Saved demo fixture is not valid JSON: {path}") from exc
    required = {"case_id", "image_path", "image_name", "report", "labels", "result"}
    missing = sorted(required - fixture.keys())
    if missing:
        raise ValueError(f"Saved demo fixture is missing: {', '.join(missing)}")
    return fixture


def _fixture_image_path(fixture: dict[str, Any]) -> Path:
    image_path = Path(str(fixture["image_path"]))
    return image_path if image_path.is_absolute() else ROOT / image_path


def demo_case_payload(path: Path) -> dict[str, Any]:
    fixture = load_demo_fixture(path)
    image_path = _fixture_image_path(fixture)
    try:
        image_bytes = image_path.read_bytes()
    except FileNotFoundError as exc:
        raise ValueError(f"Saved demo image was not found: {image_path}") from exc
    expected_sha256 = str(fixture.get("image_sha256", ""))
    if expected_sha256 and hashlib.sha256(image_bytes).hexdigest() != expected_sha256:
        raise ValueError("Saved demo image checksum does not match the replay fixture.")
    mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
    return {
        "case_id": fixture["case_id"],
        "image": f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}",
        "image_name": fixture["image_name"],
        "report": fixture["report"],
        "labels": fixture["labels"],
    }


def replay_result(
    path: Path,
    case_id: str,
    report: str,
    labels: list[str],
) -> dict[str, Any]:
    fixture = load_demo_fixture(path)
    if case_id != fixture["case_id"]:
        raise ValueError("Saved replay mode only supports the bundled demo case. Select Load demo case first.")
    if report != fixture["report"] or labels != fixture["labels"]:
        raise ValueError("The bundled demo case was changed. Select Load demo case again before replaying it.")
    result = copy.deepcopy(fixture["result"])
    result["demo_replay"] = True
    result["demo_case_id"] = fixture["case_id"]
    return result


def demo_model_statuses() -> dict[str, dict[str, Any]]:
    return {
        model: {
            "configured": True,
            "backend": "saved-replay",
            "detail": f"{display_name} saved benchmark output",
        }
        for model, display_name in DEMO_MODELS.items()
    }
