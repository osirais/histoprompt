from types import SimpleNamespace
from unittest.mock import patch

from ashby.musk_backend import RemoteMusk


def test_remote_musk_uses_ncsa_contract():
    settings = SimpleNamespace(
        musk_endpoint="http://127.0.0.1:8801",
        musk_api_key="secret",
    )
    captured = {}

    def fake_post(url, payload, headers):
        captured.update(url=url, payload=payload, headers=headers)
        return {"results": [{"predicted_label": "tumor", "score": 0.72}]}

    with patch("ashby.musk_backend._post_json", side_effect=fake_post):
        predictions = RemoteMusk(settings).classify(
            "data:image/jpeg;base64,YQ==", ["tumor", "benign tissue"]
        )

    assert captured["url"] == "http://127.0.0.1:8801/classify"
    assert captured["headers"] == {"Authorization": "Bearer secret"}
    assert captured["payload"] == {
        "images": ["YQ=="],
        "prompts": {
            "tumor": "a histopathology image of tumor",
            "benign tissue": "a histopathology image of benign tissue",
        },
    }
    assert predictions[0].label == "tumor"
    assert predictions[0].probability == 0.72

