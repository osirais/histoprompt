from __future__ import annotations

import json

import pytest

from histoprompt.benchmark import (
    generate_evidence_prompts,
    load_manifest,
    prompts_for_strategy,
    summarize_results,
)
from histoprompt.rag import Evidence


CURATED = {"normal": "normal tissue with bland cells", "disease": "disease with atypical cells"}


def test_prompt_strategies_are_deterministic_and_keep_labels() -> None:
    assert prompts_for_strategy("label_only", CURATED) == {
        "normal": "normal",
        "disease": "disease",
    }
    assert prompts_for_strategy("generic", CURATED)["disease"] == "a histopathology image showing disease"
    assert prompts_for_strategy("curated", CURATED) == CURATED
    generated = {"normal": "generated normal", "disease": "generated disease"}
    assert prompts_for_strategy("evidence_generated", CURATED, generated) == generated


def test_manifest_rejects_ground_truth_outside_candidate_family() -> None:
    manifest = {
        "families": {"organ": {"prompts": CURATED}},
        "cases": [
            {
                "id": "case-1",
                "family": "organ",
                "ground_truth": "secret answer",
                "image_url": "https://example.test/image.jpg",
                "source_url": "https://example.test/source",
            }
        ],
    }
    with pytest.raises(ValueError, match="not a family label"):
        load_manifest(manifest)


def test_summary_excludes_failures_from_accuracy_denominator() -> None:
    rows = [
        {"strategy": "generic", "correct": True, "score": 0.8, "error": ""},
        {"strategy": "generic", "correct": False, "score": 0.6, "error": ""},
        {"strategy": "generic", "correct": False, "score": None, "error": "timeout"},
    ]
    summary = summarize_results(rows)["generic"]
    assert summary == {
        "attempted": 3,
        "successful": 2,
        "correct": 1,
        "accuracy": 0.5,
        "mean_top_score": 0.7,
    }


def test_evidence_prompt_generation_does_not_receive_curated_answers() -> None:
    class FakeIndex:
        def search(self, query: str, limit: int) -> list[Evidence]:
            assert "secret morphology" not in query
            return [Evidence("source", "title", "retrieved morphology")]

    class FakeLumen:
        def complete(self, system: str, prompt: str, model: str) -> tuple[str, str]:
            assert "secret morphology" not in prompt
            assert "ground_truth" not in prompt
            return json.dumps({"features": {"normal": "bland cells", "disease": "atypical cells"}}), "test-model"

    prompts, model, evidence = generate_evidence_prompts(
        "organ",
        {"normal": "secret morphology one", "disease": "secret morphology two"},
        FakeIndex(),  # type: ignore[arg-type]
        FakeLumen(),  # type: ignore[arg-type]
    )
    assert prompts["normal"] == "normal with bland cells"
    assert model == "test-model"
    assert evidence[0]["source_id"] == "source"
