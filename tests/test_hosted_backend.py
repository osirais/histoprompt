from types import SimpleNamespace
from unittest.mock import patch

import pytest

from histoprompt.hosted_backend import (
    HostedModelError,
    RemoteHostedModel,
    make_benchmark_backend,
)


def test_remote_hosted_model_batches_images_and_preserves_order() -> None:
    captured = {}

    def fake_post(model_name, url, payload, headers):
        captured.update(
            model_name=model_name, url=url, payload=payload, headers=headers
        )
        return {
            "results": [
                {"predicted_label": "first", "score": 0.6},
                {"predicted_label": "second", "score": 0.7},
            ]
        }

    with patch("histoprompt.hosted_backend._post_json", side_effect=fake_post):
        predictions = RemoteHostedModel(
            "QuiltNet-B-32", "http://127.0.0.1:8803", "secret"
        ).classify_batch(
            ["data:image/jpeg;base64,YQ==", "data:image/jpeg;base64,Yg=="],
            {"first": "first prompt", "second": "second prompt"},
        )

    assert captured == {
        "model_name": "QuiltNet-B-32",
        "url": "http://127.0.0.1:8803/classify",
        "payload": {
            "images": ["YQ==", "Yg=="],
            "prompts": {"first": "first prompt", "second": "second prompt"},
        },
        "headers": {"Authorization": "Bearer secret"},
    }
    assert [prediction.label for prediction in predictions] == ["first", "second"]


def test_remote_hosted_model_rejects_partial_response() -> None:
    with patch(
        "histoprompt.hosted_backend._post_json",
        return_value={"results": [{"predicted_label": "first", "score": 0.6}]},
    ):
        with pytest.raises(HostedModelError, match="1 results for 2 images"):
            RemoteHostedModel("PLIP", "http://127.0.0.1:8804", "secret").classify_batch(
                ["data:image/jpeg;base64,YQ==", "data:image/jpeg;base64,Yg=="],
                {"first": "first prompt"},
            )


def test_remote_hosted_model_exposes_probability() -> None:
    with patch(
        "histoprompt.hosted_backend._post_json",
        return_value={"results": [{"predicted_label": "first", "score": 0.6}]},
    ):
        result = RemoteHostedModel(
            "PLIP", "http://127.0.0.1:8804", "secret"
        ).classify_batch(
            ["data:image/jpeg;base64,YQ=="],
            {"first": "first prompt"},
        )[0]

    assert result.label == "first"
    assert result.probability == 0.6


def test_benchmark_backend_reads_quiltnet_environment(monkeypatch) -> None:
    monkeypatch.setenv("QUILTNET_ENDPOINT", "http://127.0.0.1:8803")
    monkeypatch.setenv("QUILTNET_API_KEY", "secret")
    settings = SimpleNamespace()

    backend = make_benchmark_backend(settings, "quiltnet")

    assert backend.model_name == "QuiltNet-B-32"
    assert backend.endpoint == "http://127.0.0.1:8803"
