from ashby.pipeline import _json_from_model


def test_extracts_plain_json():
    assert _json_from_model('{"classification":"test"}') == {"classification": "test"}


def test_extracts_fenced_json():
    assert _json_from_model('```json\n{"confidence":0.5}\n```') == {"confidence": 0.5}


def test_rejects_non_json():
    assert _json_from_model("not structured") is None

