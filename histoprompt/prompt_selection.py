from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any, Iterable


def split_case_ids(
    cases: list[dict[str, Any]], development_fraction: float = 0.5
) -> tuple[set[str], set[str]]:
    """Create a deterministic, class-stratified development/test split."""
    if not 0 < development_fraction < 1:
        raise ValueError("development_fraction must be between 0 and 1")
    grouped: dict[tuple[str, str], list[str]] = {}
    for case in cases:
        key = (str(case["family"]), str(case["ground_truth"]))
        grouped.setdefault(key, []).append(str(case["case_id"]))

    development: set[str] = set()
    test: set[str] = set()
    for case_ids in grouped.values():
        if len(case_ids) < 2:
            raise ValueError("Every family/label group needs at least two cases")
        boundary = max(1, min(len(case_ids) - 1, int(len(case_ids) * development_fraction)))
        development.update(case_ids[:boundary])
        test.update(case_ids[boundary:])
    return development, test


def majority_prediction(
    rows_by_strategy: dict[str, dict[str, Any]], strategies: tuple[str, ...]
) -> str | None:
    predictions = [
        rows_by_strategy[strategy].get("prediction")
        for strategy in strategies
        if strategy in rows_by_strategy and not rows_by_strategy[strategy].get("error")
    ]
    predictions = [str(prediction) for prediction in predictions if prediction]
    if not predictions:
        return None
    counts = Counter(predictions)
    highest = max(counts.values())
    winners = {label for label, count in counts.items() if count == highest}
    generic_prediction = rows_by_strategy.get("generic", {}).get("prediction")
    if generic_prediction in winners:
        return str(generic_prediction)
    return next(prediction for prediction in predictions if prediction in winners)


def evaluate_candidate(
    rows: list[dict[str, Any]],
    case_ids: set[str],
    strategies: tuple[str, ...],
) -> dict[str, Any]:
    by_case: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        case_id = str(row.get("case_id", ""))
        strategy = str(row.get("strategy", ""))
        if case_id in case_ids and strategy in strategies:
            by_case.setdefault(case_id, {})[strategy] = row

    correct = 0
    attempted = 0
    per_label: dict[str, dict[str, int]] = {}
    for rows_by_strategy in by_case.values():
        if not all(strategy in rows_by_strategy for strategy in strategies):
            continue
        first = rows_by_strategy[strategies[0]]
        prediction = majority_prediction(rows_by_strategy, strategies)
        if prediction is None:
            continue
        truth = str(first["ground_truth"])
        attempted += 1
        is_correct = prediction == truth
        correct += is_correct
        counts = per_label.setdefault(truth, {"correct": 0, "attempted": 0})
        counts["correct"] += is_correct
        counts["attempted"] += 1

    label_accuracies = [
        counts["correct"] / counts["attempted"]
        for counts in per_label.values()
        if counts["attempted"]
    ]
    return {
        "strategies": list(strategies),
        "correct": correct,
        "attempted": attempted,
        "accuracy": correct / attempted if attempted else 0.0,
        "balanced_accuracy": (
            sum(label_accuracies) / len(label_accuracies) if label_accuracies else 0.0
        ),
        "per_label": per_label,
    }


def select_prompt_candidate(
    rows: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    strategies: Iterable[str],
) -> dict[str, Any]:
    """Select on development cases, then evaluate once on untouched cases."""
    available = tuple(dict.fromkeys(strategies))
    if "generic" not in available:
        raise ValueError("generic must be included as the baseline")
    development_ids, test_ids = split_case_ids(cases)
    candidates = [(strategy,) for strategy in available]
    candidates.extend(
        combination
        for size in range(3, len(available) + 1, 2)
        for combination in combinations(available, size)
        if "generic" in combination
    )
    development_results = [
        evaluate_candidate(rows, development_ids, candidate) for candidate in candidates
    ]
    winner = max(
        development_results,
        key=lambda item: (
            item["balanced_accuracy"],
            item["accuracy"],
            item["strategies"] == ["generic"],
            -len(item["strategies"]),
        ),
    )
    selected = tuple(winner["strategies"])
    return {
        "method": "class-stratified first-half development / second-half held-out test",
        "selection_metric": "development balanced accuracy",
        "development_cases": len(development_ids),
        "test_cases": len(test_ids),
        "candidates": development_results,
        "selected_strategies": list(selected),
        "development": winner,
        "held_out_test": evaluate_candidate(rows, test_ids, selected),
        "generic_held_out_test": evaluate_candidate(rows, test_ids, ("generic",)),
    }
