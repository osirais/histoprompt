from types import SimpleNamespace
from unittest.mock import patch

import pytest

from histoprompt.musk_backend import MuskError, RemoteMusk


def test_remote_musk_uses_ncsa_contract():
    settings = SimpleNamespace(
        musk_endpoint="http://127.0.0.1:8801",
        musk_api_key="secret",
    )
    captured = {}

    def fake_post(url, payload, headers):
        captured.update(url=url, payload=payload, headers=headers)
        return {"results": [{"predicted_label": "tumor", "score": 0.72}]}

    with patch("histoprompt.musk_backend._post_json", side_effect=fake_post):
        predictions = RemoteMusk(settings).classify(
            "data:image/jpeg;base64,YQ==",
            {
                "tumor": "a histopathology image showing malignant tumor cells",
                "benign tissue": "a histopathology image showing benign tissue",
            },
        )

    assert captured["url"] == "http://127.0.0.1:8801/classify"
    assert captured["headers"] == {"Authorization": "Bearer secret"}
    assert captured["payload"] == {
        "images": ["YQ=="],
        "prompts": {
            "tumor": "a histopathology image showing malignant tumor cells",
            "benign tissue": "a histopathology image showing benign tissue",
        },
    }
    assert predictions[0].label == "tumor"
    assert predictions[0].probability == 0.72


def test_remote_musk_batches_images_and_preserves_response_order():
    settings = SimpleNamespace(
        musk_endpoint="http://127.0.0.1:8801",
        musk_api_key="",
    )
    captured = {}

    def fake_post(url, payload, headers):
        captured.update(payload=payload)
        return {
            "results": [
                {"predicted_label": "first", "score": 0.51},
                {"predicted_label": "second", "score": 0.99},
            ]
        }

    with patch("histoprompt.musk_backend._post_json", side_effect=fake_post):
        predictions = RemoteMusk(settings).classify_batch(
            ["data:image/jpeg;base64,YQ==", "data:image/jpeg;base64,Yg=="],
            {"first": "first prompt", "second": "second prompt"},
        )

    assert captured["payload"]["images"] == ["YQ==", "Yg=="]
    assert [prediction.label for prediction in predictions] == ["first", "second"]


def test_remote_musk_rejects_partial_batch_response():
    settings = SimpleNamespace(
        musk_endpoint="http://127.0.0.1:8801",
        musk_api_key="",
    )

    with patch(
        "histoprompt.musk_backend._post_json",
        return_value={"results": [{"predicted_label": "first", "score": 0.51}]},
    ):
        with pytest.raises(MuskError, match="1 results for 2 images"):
            RemoteMusk(settings).classify_batch(
                ["data:image/jpeg;base64,YQ==", "data:image/jpeg;base64,Yg=="],
                {"first": "first prompt", "second": "second prompt"},
            )

