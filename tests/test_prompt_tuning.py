from collections import Counter

import pytest

from histoprompt.prompt_tuning import (
    DEFAULT_TEMPLATE,
    compare,
    overlap_filter,
    parse_candidates,
    passes_confirmation,
    passes_tuning_bars,
    prompts_from_full_tuning,
    sign_test_p,
    select_base,
    template_prompts,
    tune,
)

LABELS = ["benign lung tissue", "lung adenocarcinoma", "lung squamous cell carcinoma"]


def test_template_prompts_add_phrase_only_where_set():
    prompts = template_prompts(LABELS, {"benign lung tissue": "intact alveolar sacs"})
    assert prompts["benign lung tissue"] == "histology showing benign lung tissue with intact alveolar sacs"
    assert prompts["lung adenocarcinoma"] == "histology showing lung adenocarcinoma"


def test_sign_test():
    assert sign_test_p(0, 0) == 1.0
    assert sign_test_p(7, 0) == 1 / 128
    assert sign_test_p(41, 30) > 0.05


def test_bars_need_both_accuracy_and_significance():
    current = [False] * 100 + [True] * 800
    clear_win = compare([True] * 12 + [False] * 88 + [True] * 800, current)
    assert passes_tuning_bars(clear_win)
    churn = compare([True] * 41 + [False] * 59 + [False] * 30 + [True] * 770, current)
    assert churn.gain >= 0.01 and not passes_tuning_bars(churn)        # +1.2 points, but 41 fixed / 30 broken
    tiny = compare([True] * 5 + [False] * 95 + [True] * 800, current)
    assert not passes_tuning_bars(tiny)                                 # significant-looking but under +1 point
    assert passes_confirmation(compare([True] * 5 + [False] * 95 + [True] * 800, current))


def test_overlap_filter_drops_shared_words():
    kept, dropped = overlap_filter(
        {"benign lung tissue": ["thin alveolar walls"], "lung adenocarcinoma": ["lepidic growth along alveolar walls", "glandular lumina"]},
        LABELS[:2],
    )
    assert kept == {"benign lung tissue": [], "lung adenocarcinoma": ["glandular lumina"]}
    assert len(dropped) == 2


def test_parse_candidates_cleans_and_limits():
    raw = '{"candidates": {"Lung Adenocarcinoma": ["Glandular Lumina!", "", "acinar pattern"]}}'
    assert parse_candidates(raw, ["lung adenocarcinoma"], 1) == {"lung adenocarcinoma": ["glandular lumina"]}


def test_tune_accepts_only_confirmed_significant_gains():
    good = "histology showing benign lung tissue with intact alveolar sacs"

    def evaluate(prompts):                            # the good phrase fixes 12 of 100 images, others change nothing
        fixed = 12 if prompts["benign lung tissue"] == good else 0
        return [True] * (800 + fixed) + [False] * (100 - fixed)

    def propose(focus, confusion):
        if focus:
            return {focus: ["acinar pattern"]}
        return {"benign lung tissue": ["intact alveolar sacs", "thin septa"], "lung adenocarcinoma": ["glandular lumina"]}

    chosen = tune(LABELS, evaluate, evaluate, propose, lambda prompts: Counter({("lung adenocarcinoma", "x"): 1}))
    assert chosen == {"benign lung tissue": "intact alveolar sacs", "lung adenocarcinoma": "", "lung squamous cell carcinoma": ""}


def test_template_prompts_supports_a_model_specific_base():
    prompts = template_prompts(
        LABELS[:1],
        {"benign lung tissue": "clear air spaces"},
        "an H&E image of {label}.",
    )
    assert prompts == {
        "benign lung tissue": "an H&E image of benign lung tissue with clear air spaces."
    }


def test_prompts_from_full_tuning_rejects_template_only_output():
    result = {
        "template_only": True,
        "base_template": "an H&E image of {label}.",
        "chosen_phrases": {"lung adenocarcinoma": "glandular lumina"},
    }
    with pytest.raises(ValueError, match="full tuning result"):
        prompts_from_full_tuning(LABELS, result)


def test_prompts_from_full_tuning_applies_only_accepted_matching_phrases():
    result = {
        "template_only": False,
        "base_template": "an H&E image of {label}.",
        "chosen_phrases": {
            "benign lung tissue": "",
            "lung adenocarcinoma": "glandular lumina",
        },
    }
    prompts, tuned_labels = prompts_from_full_tuning(
        ["lung adenocarcinoma", "breast invasive carcinoma"], result
    )
    assert prompts == {
        "lung adenocarcinoma": "an H&E image of lung adenocarcinoma with glandular lumina.",
        "breast invasive carcinoma": "an H&E image of breast invasive carcinoma.",
    }
    assert tuned_labels == ["lung adenocarcinoma"]


def _scorer(scores):
    def evaluate(prompts):
        base = next(iter(prompts.values())).replace("benign lung tissue", "{label}")
        right = scores.get(base, 800)
        return [True] * right + [False] * (900 - right)

    return evaluate


def test_select_base_switches_only_on_a_clear_confirmed_win():
    templates = [DEFAULT_TEMPLATE, "a histopathology image showing {label}", "{label}"]
    clear = _scorer(
        {DEFAULT_TEMPLATE: 600, "a histopathology image showing {label}": 840}
    )
    assert (
        select_base(LABELS[:1], clear, clear, templates)
        == "a histopathology image showing {label}"
    )

    marginal = _scorer(
        {DEFAULT_TEMPLATE: 800, "a histopathology image showing {label}": 804}
    )
    assert select_base(LABELS[:1], marginal, marginal, templates) == DEFAULT_TEMPLATE

    unconfirmed = _scorer(
        {DEFAULT_TEMPLATE: 800, "a histopathology image showing {label}": 830}
    )
    flat = _scorer({})
    assert select_base(LABELS[:1], unconfirmed, flat, templates) == DEFAULT_TEMPLATE
