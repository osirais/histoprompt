from types import SimpleNamespace
from unittest.mock import patch

import pytest

from histoprompt.conch_backend import ConchError, RemoteConch, conch_status


def _settings(**overrides):
    values = {
        "conch_backend": "remote",
        "conch_endpoint": "http://127.0.0.1:8802",
        "conch_api_key": "test-key",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_remote_conch_uses_shared_classify_contract():
    with patch(
        "histoprompt.conch_backend._post_json",
        return_value={"results": [{"predicted_label": "tumor", "score": 0.8}]},
    ) as post:
        result = RemoteConch(_settings()).classify(
            "data:image/jpeg;base64,YQ==", {"tumor": "histology showing tumor"}
        )

    assert result[0].label == "tumor"
    assert result[0].probability == 0.8
    assert post.call_args.args[0] == "http://127.0.0.1:8802/classify"
    assert post.call_args.args[2] == {"Authorization": "Bearer test-key"}
    assert post.call_args.args[1]["prompts"] == {"tumor": "histology showing tumor"}


def test_remote_conch_rejects_missing_key():
    with pytest.raises(ConchError, match="CONCH_API_KEY"):
        RemoteConch(_settings(conch_api_key=""))


def test_disabled_conch_is_explicitly_not_configured():
    assert conch_status(_settings(conch_backend="disabled"))["configured"] is False
