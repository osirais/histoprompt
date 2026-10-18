"""Aggregation helpers for the PathGen clinician-workflow benchmark."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Sequence

from .pathgen_benchmark import accuracy_summary, paired_changes


def select_cases(
    cases: Sequence[dict[str, Any]],
    *,
    per_project: int | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    if per_project is not None and per_project < 1:
        raise ValueError("per_project must be positive")
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
    if per_project is None:
        selected = list(cases)
    else:
        counts: dict[str, int] = defaultdict(int)
        selected = []
        for case in cases:
            project = str(case["project_id"])
            if counts[project] < per_project:
                selected.append(case)
                counts[project] += 1
    return selected[:limit] if limit is not None else selected


def summarize_workflow(
    cases: Sequence[dict[str, Any]],
    results: Sequence[dict[str, Any]],
    models: Sequence[str],
) -> dict[str, Any]:
    if [case["case_id"] for case in cases] != [
        result["case_id"] for result in results
    ]:
        raise ValueError("Workflow results must match the selected case order.")
    model_summaries: dict[str, Any] = {}
    for model in models:
        baseline = [
            str(result["model_results"][model]["baseline"]["label"])
            for result in results
        ]
        enhanced = [
            str(result["model_results"][model]["enhanced"]["label"])
            for result in results
        ]
        paired = paired_changes(cases, baseline, enhanced)
        paired["per_project"] = {
            project: paired_changes(
                [case for case in cases if str(case["project_id"]) == project],
                [
                    prediction
                    for case, prediction in zip(cases, baseline)
                    if str(case["project_id"]) == project
                ],
                [
                    prediction
                    for case, prediction in zip(cases, enhanced)
                    if str(case["project_id"]) == project
                ],
            )
            for project in sorted({str(case["project_id"]) for case in cases})
        }
        model_summaries[model] = {
            "baseline": accuracy_summary(cases, baseline),
            "enhanced": accuracy_summary(cases, enhanced),
            "paired": paired,
        }
    final = [str(result["final_classification"]) for result in results]
    return {
        "cases": len(cases),
        "models": model_summaries,
        "final_review": accuracy_summary(cases, final),
    }
