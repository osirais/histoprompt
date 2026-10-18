import json
from types import SimpleNamespace
from unittest.mock import patch

from histoprompt.musk_backend import Prediction
from histoprompt.pipeline import AnalysisPipeline, _extract_prompts, _json_from_model
from histoprompt.rag import EvidenceIndex


def test_extracts_plain_json():
    assert _json_from_model('{"classification":"test"}') == {"classification": "test"}


def test_extracts_fenced_json():
    assert _json_from_model('```json\n{"confidence":0.5}\n```') == {"confidence": 0.5}


def test_rejects_non_json():
    assert _json_from_model("not structured") is None


def test_prompt_extraction_preserves_labels_and_falls_back():
    prompts = _extract_prompts(
        {"features": {"Tumor": "gland-forming malignant cells"}},
        ["tumor", "benign tissue"],
    )
    assert prompts == {
        "tumor": "tumor with gland-forming malignant cells",
        "benign tissue": "a histopathology image showing benign tissue",
    }


def test_pipeline_enriches_prompts_before_musk(tmp_path):
    events = []
    captured = {}
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(
        json.dumps(
            {
                "source_id": "source-1",
                "title": "Tumor morphology",
                "text": "Tumors can show malignant gland formation.",
            }
        ),
        encoding="utf-8",
    )

    class FakeLumen:
        def complete(self, system, prompt, model):
            if not events:
                events.append("prompt enrichment")
                return (
                    json.dumps(
                        {
                            "features": {
                                "tumor": "malignant gland formation",
                                "benign": "orderly benign glands",
                            }
                        }
                    ),
                    "test-model",
                )
            events.append("evidence review")
            return (
                json.dumps(
                    {
                        "assessment": "review",
                        "classification": "tumor",
                        "confidence": 0.7,
                    }
                ),
                "test-model",
            )

    class FakeMusk:
        calls = 0

        def classify(self, image, prompts):
            self.calls += 1
            events.append({1: "musk baseline", 2: "musk enriched"}[self.calls])
            if self.calls == 2:
                captured.update(prompts)
            return [Prediction("tumor", 0.7)]

    pipeline = AnalysisPipeline(
        SimpleNamespace(), EvidenceIndex(corpus), FakeLumen()
    )
    with patch("histoprompt.pipeline.make_benchmark_backend", return_value=FakeMusk()):
        result = pipeline.analyze(
            {
                "image": "data:image/jpeg;base64,YQ==",
                "report": "Malignant gland formation.",
                "labels": ["tumor", "benign"],
                "top_k": 1,
            }
        )

    assert events == [
        "prompt enrichment",
        "musk baseline",
        "musk enriched",
        "evidence review",
    ]
    assert captured["tumor"] == "tumor with malignant gland formation"
    assert result["musk_prompts"] == captured
    assert result["primary_prompts"] == captured
    assert result["primary_predictions"] == result["musk_predictions"]
    assert result["primary_classification_source"] == "case-specific Lumen prompt with MUSK"
    assert result["final_classification"] == "tumor"
    assert result["model_results"]["musk"]["enhanced"]["label"] == "tumor"


def test_pipeline_compares_each_configured_model_with_case_specific_prompts(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(
        json.dumps(
            {
                "source_id": "source-1",
                "title": "Tumor morphology",
                "text": "Tumors can show malignant gland formation.",
            }
        ),
        encoding="utf-8",
    )
    review_requests = []

    class FakeLumen:
        calls = 0

        def complete(self, system, prompt, model):
            self.calls += 1
            if self.calls == 1:
                return (
                    json.dumps(
                        {
                            "features": {
                                "tumor": "malignant gland formation",
                                "benign": "orderly benign glands",
                            }
                        }
                    ),
                    "test-model",
                )
            review_requests.append(prompt)
            return (
                json.dumps(
                    {
                        "assessment": "Model outputs support the tumor candidate.",
                        "classification": "tumor",
                        "confidence": 0.7,
                    }
                ),
                "test-model",
            )

    class FakeBackend:
        def __init__(self, name):
            self.name = name
            self.calls = []

        def classify(self, image, prompts):
            self.calls.append(prompts)
            score = 0.6 if len(self.calls) == 1 else 0.7
            return [Prediction("tumor", score)]

    backends = {
        name: FakeBackend(name) for name in ("musk", "conch", "quiltnet", "plip")
    }
    settings = SimpleNamespace(
        conch_backend="remote",
        quiltnet_endpoint="http://quiltnet",
        quiltnet_api_key="quiltnet-key",
        plip_endpoint="http://plip",
        plip_api_key="plip-key",
    )
    pipeline = AnalysisPipeline(settings, EvidenceIndex(corpus), FakeLumen())

    with patch(
        "histoprompt.pipeline.make_benchmark_backend",
        side_effect=lambda _settings, model: backends[model],
    ):
        result = pipeline.analyze(
            {
                "image": "data:image/jpeg;base64,YQ==",
                "report": "Malignant gland formation.",
                "labels": ["tumor", "benign"],
                "top_k": 1,
            }
        )

    assert list(result["model_results"]) == ["musk", "conch", "quiltnet", "plip"]
    for backend in backends.values():
        assert backend.calls == [
            {
                "tumor": "a histopathology image showing tumor",
                "benign": "a histopathology image showing benign",
            },
            {
                "tumor": "tumor with malignant gland formation",
                "benign": "benign with orderly benign glands",
            },
        ]
    assert review_requests
    for model_name in ("MUSK", "CONCH", "QUILTNET", "PLIP"):
        assert model_name in review_requests[0]

