from histoprompt.prompt_selection import (
    majority_prediction,
    select_prompt_candidate,
    split_case_ids,
)


def _cases() -> list[dict[str, str]]:
    return [
        {"case_id": f"{label}-{index}", "family": "organ", "ground_truth": label}
        for label in ("a", "b")
        for index in range(4)
    ]


def test_split_is_stratified_and_deterministic() -> None:
    development, test = split_case_ids(_cases())

    assert development == {"a-0", "a-1", "b-0", "b-1"}
    assert test == {"a-2", "a-3", "b-2", "b-3"}


def test_majority_vote_uses_generic_to_break_a_tie() -> None:
    rows = {
        "generic": {"prediction": "a"},
        "short": {"prediction": "b"},
    }

    assert majority_prediction(rows, ("generic", "short")) == "a"


def test_selection_uses_only_development_cases_then_reports_held_out_result() -> None:
    cases = _cases()
    rows = []
    for case in cases:
        truth = case["ground_truth"]
        index = int(case["case_id"].split("-")[-1])
        for strategy in ("generic", "feature_one", "feature_two"):
            prediction = truth
            if strategy == "generic" and index < 2:
                prediction = "b" if truth == "a" else "a"
            if strategy != "generic" and index >= 2:
                prediction = "b" if truth == "a" else "a"
            rows.append(
                {
                    **case,
                    "strategy": strategy,
                    "prediction": prediction,
                    "error": "",
                }
            )

    result = select_prompt_candidate(
        rows, cases, ("generic", "feature_one", "feature_two")
    )

    assert result["selected_strategies"] == ["feature_one"]
    assert result["development"]["accuracy"] == 1.0
    assert result["held_out_test"]["accuracy"] == 0.0
    assert result["generic_held_out_test"]["accuracy"] == 1.0
