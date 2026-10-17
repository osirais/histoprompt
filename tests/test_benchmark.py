from __future__ import annotations

import json

import pytest

from histoprompt.benchmark import (
    generate_evidence_prompts,
    load_manifest,
    prompts_for_strategy,
    summarize_results,
    verify_image_checksum,
)
from histoprompt.rag import Evidence
from histoprompt.reporting import markdown_report


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


def test_manifest_expands_local_case_sets() -> None:
    manifest = {
        "families": {"organ": {"prompts": CURATED}},
        "case_sets": [
            {
                "id_prefix": "normal",
                "family": "organ",
                "ground_truth": "normal",
                "source_url": "https://example.test/source",
                "source_note": "fixed examples",
                "images": [
                    {"image_path": "benchmarks/images/one.jpg", "sha256": "abc"},
                    {"image_path": "benchmarks/images/two.jpg", "sha256": "def"},
                ],
            }
        ],
    }

    cases, _ = load_manifest(manifest)

    assert [case.case_id for case in cases] == ["normal-01", "normal-02"]
    assert cases[1].image_path == "benchmarks/images/two.jpg"
    assert cases[1].sha256 == "def"


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


def test_markdown_report_leads_with_scope_and_main_comparison() -> None:
    case = {
        "case_id": "case-1",
        "family": "lung histopathology",
        "ground_truth": "lung adenocarcinoma",
    }
    prompts = {
        "lung adenocarcinoma": "a histopathology image showing lung adenocarcinoma",
        "lung squamous cell carcinoma": "a histopathology image showing lung squamous cell carcinoma",
    }
    rows = [
        {
            **case,
            "strategy": strategy,
            "prompts": prompts,
            "prediction": "lung adenocarcinoma" if strategy == "generic" else "lung squamous cell carcinoma",
            "correct": strategy == "generic",
        }
        for strategy in ("generic", "evidence_generated")
    ]
    summary_item = {"correct": 1, "successful": 1, "accuracy": 1.0, "mean_top_score": 0.5}
    result = {
        "run_id": "test-run",
        "cases": [case],
        "results": rows,
        "summary": {
            "label_only": summary_item,
            "generic": summary_item,
            "curated": {**summary_item, "correct": 0, "accuracy": 0.0},
            "evidence_generated": {**summary_item, "correct": 0, "accuracy": 0.0},
        },
    }

    report = markdown_report(result)

    assert "## Short answer" in report
    assert "Original MUSK classified 1 of 1 images correctly" in report
    assert "Enhanced MUSK classified 0 of 1 images correctly" in report
    assert "## What we tested" in report
    assert "Worse; changed a correct result to an error" in report
    assert "## What a broader benchmark should add" in report


def test_local_benchmark_image_checksum_is_enforced(tmp_path) -> None:
    image = tmp_path / "image.jpg"
    image.write_bytes(b"fixed image bytes")

    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_image_checksum(image.read_bytes(), "0" * 64, "fixed-case")
