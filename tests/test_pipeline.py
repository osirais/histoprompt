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
            events.append(
                {1: "musk baseline", 2: "musk short-template", 3: "musk enriched"}[self.calls]
            )
            if self.calls == 3:
                captured.update(prompts)
            return [Prediction("tumor", 0.7)]

    pipeline = AnalysisPipeline(
        SimpleNamespace(), EvidenceIndex(corpus), FakeLumen()
    )
    with patch("histoprompt.pipeline.make_musk_backend", return_value=FakeMusk()):
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
        "musk short-template",
        "musk enriched",
        "evidence review",
    ]
    assert captured["tumor"] == "tumor with malignant gland formation"
    assert result["musk_prompts"] == captured
    assert result["primary_prompts"]["tumor"] == "histology showing tumor"
    assert result["primary_predictions"] == result["musk_predictions"]
    assert result["primary_classification_source"] == "short histology-template MUSK"

