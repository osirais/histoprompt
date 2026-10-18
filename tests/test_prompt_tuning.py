from collections import Counter

from histoprompt.prompt_tuning import (
    compare,
    overlap_filter,
    parse_candidates,
    passes_confirmation,
    passes_tuning_bars,
    sign_test_p,
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


def test_template_prompts_with_other_base():
    prompts = template_prompts(LABELS[:1], {"benign lung tissue": "clear air spaces"}, "an H&E image of {label}")
    assert prompts == {"benign lung tissue": "an H&E image of benign lung tissue with clear air spaces"}


def _scorer(scores):
    """Evaluate function where each base template gets a fixed number of 900 images right."""
    def evaluate(prompts):
        base = next(iter(prompts.values())).replace("benign lung tissue", "{label}")
        right = scores.get(base, 800)
        return [True] * right + [False] * (900 - right)
    return evaluate


def test_select_base_switches_only_on_a_clear_confirmed_win():
    from histoprompt.prompt_tuning import DEFAULT_TEMPLATE, select_base
    labels = ["benign lung tissue"]
    templates = [DEFAULT_TEMPLATE, "a histopathology image showing {label}", "{label}"]
    clear = _scorer({DEFAULT_TEMPLATE: 600, "a histopathology image showing {label}": 840})
    assert select_base(labels, clear, clear, templates) == "a histopathology image showing {label}"
    marginal = _scorer({DEFAULT_TEMPLATE: 800, "a histopathology image showing {label}": 804})
    assert select_base(labels, marginal, marginal, templates) == DEFAULT_TEMPLATE      # +0.4 points: kept default
    unconfirmed = _scorer({DEFAULT_TEMPLATE: 800, "a histopathology image showing {label}": 830})
    flat = _scorer({})
    assert select_base(labels, unconfirmed, flat, templates) == DEFAULT_TEMPLATE        # not confirmed
