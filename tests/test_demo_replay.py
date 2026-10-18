import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from histoprompt.demo_replay import demo_case_payload, demo_model_statuses, replay_result
from histoprompt.pipeline import AnalysisPipeline
from histoprompt.rag import EvidenceIndex


def _fixture(tmp_path: Path) -> tuple[Path, dict]:
    image = tmp_path / "case.jpeg"
    image.write_bytes(b"demo-image")
    data = {
        "case_id": "case-1",
        "image_path": str(image),
        "image_sha256": hashlib.sha256(b"demo-image").hexdigest(),
        "image_name": "case.jpeg",
        "report": "Case findings.",
        "labels": ["candidate a", "candidate b"],
        "result": {"final_classification": "candidate a"},
    }
    path = tmp_path / "demo.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, data


def test_demo_case_includes_bundled_image_as_data_url(tmp_path):
    path, data = _fixture(tmp_path)

    payload = demo_case_payload(path)

    assert payload["case_id"] == data["case_id"]
    assert payload["image"].startswith("data:image/jpeg;base64,")
    assert payload["labels"] == data["labels"]


def test_replay_accepts_only_the_unchanged_bundled_case(tmp_path):
    path, data = _fixture(tmp_path)

    result = replay_result(path, data["case_id"], data["report"], data["labels"])

    assert result["demo_replay"] is True
    assert result["final_classification"] == "candidate a"
    with pytest.raises(ValueError, match="Load demo case"):
        replay_result(path, "another-case", data["report"], data["labels"])
    with pytest.raises(ValueError, match="changed"):
        replay_result(path, data["case_id"], "Edited report.", data["labels"])


def test_pipeline_replay_makes_no_live_calls(tmp_path):
    path, data = _fixture(tmp_path)
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text('{"source_id":"s","title":"t","text":"body"}\n', encoding="utf-8")

    class FailLumen:
        def complete(self, *_args):
            raise AssertionError("Lumen must not run during saved replay")

    settings = SimpleNamespace(demo_replay=True, demo_replay_path=path)
    pipeline = AnalysisPipeline(settings, EvidenceIndex(corpus), FailLumen())

    result = pipeline.analyze(
        {
            "image": "data:image/jpeg;base64,ZGVtbw==",
            "report": data["report"],
            "labels": data["labels"],
            "demo_case_id": data["case_id"],
        }
    )

    assert result["demo_replay"] is True


def test_demo_status_marks_all_four_models_as_saved_replays():
    statuses = demo_model_statuses()

    assert set(statuses) == {"musk", "conch", "quiltnet", "plip"}
    assert all(status["configured"] for status in statuses.values())
    assert all(status["backend"] == "saved-replay" for status in statuses.values())
