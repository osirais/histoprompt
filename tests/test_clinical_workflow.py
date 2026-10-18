import json

from histoprompt.clinical_workflow import (
    build_prompt_generation_request,
    build_review_request,
    normalize_review_classification,
    parse_lumen_prompts,
)


LABELS = ["colon adenocarcinoma", "lung adenocarcinoma"]


def test_prompt_request_contains_real_case_inputs():
    request = build_prompt_generation_request(
        "Colon tissue with irregular malignant glands.",
        LABELS,
        "[source-1] Colorectal morphology\nMalignant glands can invade stroma.",
    )

    assert "Colon tissue with irregular malignant glands." in request
    assert json.dumps(LABELS, indent=2) in request
    assert "[source-1] Colorectal morphology" in request
    assert "ground truth" not in request.lower()


def test_lumen_prompts_preserve_every_candidate_and_fall_back():
    prompts, parsed = parse_lumen_prompts(
        '{"features":{"colon adenocarcinoma":"dirty necrosis and malignant glands"}}',
        LABELS,
    )

    assert parsed == {
        "features": {
            "colon adenocarcinoma": "dirty necrosis and malignant glands"
        }
    }
    assert prompts == {
        "colon adenocarcinoma": (
            "colon adenocarcinoma with dirty necrosis and malignant glands"
        ),
        "lung adenocarcinoma": (
            "a histopathology image showing lung adenocarcinoma"
        ),
    }


def test_review_request_contains_all_model_outputs_and_requires_exact_label():
    request = build_review_request(
        report="Colon tissue with malignant glands.",
        labels=LABELS,
        prompts={label: f"{label} with features" for label in LABELS},
        model_results={
            "musk": {
                "baseline": {"label": "lung adenocarcinoma", "probability": 0.6},
                "enhanced": {"label": "colon adenocarcinoma", "probability": 0.7},
            },
            "conch": {
                "baseline": {"label": "colon adenocarcinoma", "probability": 0.8},
                "enhanced": {"label": "colon adenocarcinoma", "probability": 0.9},
            },
        },
        evidence_text="[source-1] Evidence",
    )

    assert "MUSK" in request
    assert "CONCH" in request
    assert "IMAGE-ONLY BASELINE" in request
    assert "CASE-SPECIFIC LUMEN PROMPT" in request
    assert '"colon adenocarcinoma"' in request
    assert "one exact candidate label or indeterminate" in request


def test_review_classification_is_strictly_normalized():
    assert (
        normalize_review_classification(
            {"classification": " Colon Adenocarcinoma "}, LABELS
        )
        == "colon adenocarcinoma"
    )
    assert (
        normalize_review_classification(
            {"classification": "colon cancer"}, LABELS
        )
        == "indeterminate"
    )
    assert normalize_review_classification(None, LABELS) == "indeterminate"
