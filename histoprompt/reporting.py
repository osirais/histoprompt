from __future__ import annotations

from typing import Any


def _accuracy(item: dict[str, Any]) -> float:
    successful = int(item.get("successful", item.get("attempted", 0)))
    return int(item.get("correct", 0)) / successful if successful else 0.0


def markdown_report(result: dict[str, Any]) -> str:
    model_name = result.get("model_display_name", "MUSK")
    comparison = result.get("comparison", {})
    baseline_strategy = comparison.get("baseline_strategy", "generic")
    candidate_strategy = comparison.get("candidate_strategy", "evidence_generated")
    baseline_name = comparison.get("baseline_name", f"Original {model_name}")
    candidate_name = comparison.get("candidate_name", f"Enhanced {model_name}")
    baseline_input = comparison.get(
        "baseline_input", "Image + generic label descriptions"
    )
    candidate_input = comparison.get(
        "candidate_input", "Image + descriptions generated from retrieved evidence"
    )
    baseline_summary = result["summary"][baseline_strategy]
    candidate_summary = result["summary"][candidate_strategy]
    baseline_accuracy = _accuracy(baseline_summary)
    candidate_accuracy = _accuracy(candidate_summary)
    delta = candidate_accuracy - baseline_accuracy
    rows_by_key = {
        (row["case_id"], row["strategy"]): row for row in result["results"]
    }
    cases_by_family: dict[str, list[dict[str, Any]]] = {}
    for case in result["cases"]:
        cases_by_family.setdefault(case["family"], []).append(case)
    labels = list(dict.fromkeys(case["ground_truth"] for case in result["cases"]))
    benign_controls = [label for label in labels if "benign" in label.casefold()]
    disease_conditions = len(labels) - len(benign_controls)
    comparison_rows = []
    regressions = 0
    improvements = 0
    for case in result["cases"]:
        baseline = rows_by_key[(case["case_id"], baseline_strategy)]
        candidate = rows_by_key[(case["case_id"], candidate_strategy)]
        if baseline.get("prediction") != candidate.get("prediction"):
            comparison_rows.append((case, baseline, candidate))
        if baseline.get("correct") and not candidate.get("correct"):
            regressions += 1
        elif not baseline.get("correct") and candidate.get("correct"):
            improvements += 1

    if delta > 0:
        outcome = f"The candidate prompts improved accuracy by {delta * 100:.1f} percentage points."
    elif delta < 0:
        outcome = f"The candidate prompts reduced accuracy by {abs(delta) * 100:.1f} percentage points."
    else:
        outcome = "The candidate prompts did not change total accuracy."
    outcome += f" They fixed {improvements} original errors and introduced {regressions} new errors."

    benchmark_name = result.get("benchmark_name", "HistoPrompt multi-disease benchmark")
    report_context = result.get("report_context", {})
    sample_note = report_context.get(
        "sample_note",
        "This run vendors the exact image bytes in the repository and verifies a SHA-256 checksum before inference.",
    )
    source_note = report_context.get(
        "source_note",
        "LC25000 images use fixed evenly spaced rows from the public dataset. Infectious-esophagitis and skin-cancer images are published educational figures.",
    )
    scope_summary = report_context.get(
        "scope_summary",
        f"It covered {disease_conditions} disease conditions and {len(benign_controls)} benign "
        f"{'control' if len(benign_controls) == 1 else 'controls'}.",
    )
    comparison_explanation = comparison.get(
        "explanation",
        [
            f"**{baseline_name}:** The model received the image and a generic prompt such as `a histopathology image showing lung adenocarcinoma`.",
            f"**{candidate_name}:** HistoPrompt retrieved local evidence. Lumen converted that evidence into microscopic feature descriptions, which were sent with the same image.",
            "The benchmark did not give Lumen the image, a report, or the correct label, preventing answer leakage through the generated prompt.",
        ],
    )

    lines = [
        f"# {benchmark_name}",
        "",
        "## Short answer",
        "",
        f"{baseline_name} classified {baseline_summary['correct']} of "
        f"{baseline_summary['successful']} images correctly. {candidate_name} classified "
        f"{candidate_summary['correct']} of {candidate_summary['successful']} images correctly.",
        outcome,
        "",
        f"| Version | What {model_name} received | Correct | Accuracy | Change |",
        "|---|---|---:|---:|---:|",
        f"| **{baseline_name}** | {baseline_input} | "
        f"**{baseline_summary['correct']}/{baseline_summary['successful']}** | "
        f"**{baseline_accuracy:.1%}** | — |",
        f"| **{candidate_name}** | {candidate_input} | "
        f"**{candidate_summary['correct']}/{candidate_summary['successful']}** | "
        f"**{candidate_accuracy:.1%}** | **{delta * 100:+.1f} points** |",
        "",
        "## What we tested",
        "",
        f"This run used {len(result['cases'])} fixed public pathology images. {scope_summary}",
        "",
        f"| Clinical group | Images | Correct labels represented | Labels {model_name} chose between |",
        "|---|---:|---|---|",
    ]
    for family, cases in cases_by_family.items():
        truths = ", ".join(dict.fromkeys(case["ground_truth"] for case in cases))
        family_prompts = result.get("strategy_prompts", {}).get(family, {})
        baseline_prompts = family_prompts.get(baseline_strategy)
        if baseline_prompts is None:
            first_row = next(
                row for row in result["results"] if row["family"] == family
            )
            baseline_prompts = first_row.get("prompts", {})
        candidates = ", ".join(baseline_prompts)
        lines.append(
            f"| {family} | {len(cases)} | {truths} | {candidates} |"
        )
    lines.extend(
        [
            "",
            (
                "The table shows the number of images in each clinical group. Sample counts "
                "still differ by source, so the combined accuracy must be interpreted carefully."
                if len(cases_by_family) > 1
                else "This run deliberately focuses on one clinical group so both prompt versions are compared on the same fixed images."
            ),
            "",
            "## Results by clinical group",
            "",
            f"| Clinical group | {baseline_name} | {candidate_name} |",
            "|---|---:|---:|",
        ]
    )
    for family, cases in cases_by_family.items():
        case_ids = {case["case_id"] for case in cases}
        baseline_rows = [
            row for row in result["results"]
            if row["case_id"] in case_ids and row["strategy"] == baseline_strategy and not row.get("error")
        ]
        enhanced_rows = [
            row for row in result["results"]
            if row["case_id"] in case_ids and row["strategy"] == candidate_strategy and not row.get("error")
        ]
        baseline_correct = sum(bool(row.get("correct")) for row in baseline_rows)
        enhanced_correct = sum(bool(row.get("correct")) for row in enhanced_rows)
        lines.append(
            f"| {family} | {baseline_correct}/{len(baseline_rows)} | "
            f"{enhanced_correct}/{len(enhanced_rows)} |"
        )
    lines.extend(
        [
            "",
            "## Results by label",
            "",
            f"| Correct label | Images | {baseline_name} | {candidate_name} | Candidate prompt's most common error |",
            "|---|---:|---:|---:|---|",
        ]
    )
    label_stats = []
    for label in labels:
        baseline_rows = [
            row for row in result["results"]
            if row["ground_truth"] == label and row["strategy"] == baseline_strategy and not row.get("error")
        ]
        enhanced_rows = [
            row for row in result["results"]
            if row["ground_truth"] == label
            and row["strategy"] == candidate_strategy
            and not row.get("error")
        ]
        baseline_correct = sum(bool(row.get("correct")) for row in baseline_rows)
        enhanced_correct = sum(bool(row.get("correct")) for row in enhanced_rows)
        wrong_predictions: dict[str, int] = {}
        for row in enhanced_rows:
            if not row.get("correct"):
                prediction = str(row.get("prediction") or "Error")
                wrong_predictions[prediction] = wrong_predictions.get(prediction, 0) + 1
        common_error = (
            max(wrong_predictions.items(), key=lambda item: item[1])
            if wrong_predictions
            else None
        )
        error_text = f"{common_error[0]} ({common_error[1]})" if common_error else "None"
        label_stats.append(
            {
                "label": label,
                "baseline_correct": baseline_correct,
                "enhanced_correct": enhanced_correct,
                "total": len(baseline_rows),
                "common_error": common_error,
            }
        )
        lines.append(
            f"| {label} | {len(baseline_rows)} | {baseline_correct}/{len(baseline_rows)} | "
            f"{enhanced_correct}/{len(enhanced_rows)} | {error_text} |"
        )
    largest_decline = min(
        label_stats,
        key=lambda item: item["enhanced_correct"] - item["baseline_correct"],
    )
    decline = largest_decline["enhanced_correct"] - largest_decline["baseline_correct"]
    if decline < 0:
        lines.extend(
            [
                "",
                "## Main failure pattern",
                "",
                f"The largest decline was for {largest_decline['label']}: {baseline_name} got "
                f"{largest_decline['baseline_correct']}/{largest_decline['total']} correct, "
                f"while {candidate_name} got {largest_decline['enhanced_correct']}/{largest_decline['total']} correct.",
            ]
        )
        if largest_decline["common_error"]:
            wrong_label, wrong_count = largest_decline["common_error"]
            lines.append(
                f"{candidate_name} labeled {wrong_count}/{largest_decline['total']} of these images "
                f"as {wrong_label}."
            )
    lines.extend(
        [
            "",
            "## What the two versions mean",
            "",
            *[f"- {item}" for item in comparison_explanation],
            "",
            "## Cases where the prediction changed",
            "",
            f"| Clinical group | Correct label | {baseline_name} | {candidate_name} | Effect of candidate prompt |",
            "|---|---|---|---|---|",
        ]
    )
    for case, baseline, candidate in comparison_rows[:25]:
        baseline_prediction = baseline.get("prediction") or "Error"
        candidate_prediction = candidate.get("prediction") or "Error"
        if baseline.get("correct") and candidate.get("correct"):
            effect = "No change; both correct"
        elif baseline.get("correct") and not candidate.get("correct"):
            effect = "Worse; changed a correct result to an error"
        elif not baseline.get("correct") and candidate.get("correct"):
            effect = "Better; fixed an original error"
        else:
            effect = "No accuracy gain; both incorrect"
        lines.append(
            f"| {case['family']} | {case['ground_truth']} | {baseline_prediction} | "
            f"{candidate_prediction} | {effect} |"
        )
    if not comparison_rows:
        lines.append("| — | — | — | — | No predictions changed |")
    elif len(comparison_rows) > 25:
        lines.extend(
            [
                "",
                f"The table shows the first 25 of {len(comparison_rows)} changed predictions. "
                "The raw JSON contains every case.",
            ]
        )
    secondary_rows = []
    secondary_labels = {
        "label_only": "Label text only",
        "curated": "Hand-written microscopic features",
        "generic_with_features": "Generic template + all generated features",
        "generic_with_primary_feature": "Generic template + first generated feature",
    }
    for strategy, display_label in secondary_labels.items():
        item = result["summary"].get(strategy, {})
        if item.get("successful"):
            secondary_rows.append(
                f"| {display_label} | {item['correct']}/{item['successful']} | "
                f"{_accuracy(item):.1%} |"
            )
    if secondary_rows:
        lines.extend(
            [
                "",
                "## Other prompt versions",
                "",
                "The runner also tested diagnostic variants. These are secondary results, not the main product comparison.",
                "",
                "| Prompt version | Correct | Accuracy |",
                "|---|---:|---:|",
                *secondary_rows,
                "",
                "These extra variants help separate the effect of retrieval from the effect of adding longer microscopic descriptions.",
            ]
        )
    prompt_selection = result.get("prompt_selection", {})
    if prompt_selection:
        selected = prompt_selection["selected_strategies"]
        development = prompt_selection["development"]
        held_out = prompt_selection["held_out_test"]
        held_out_generic = prompt_selection["generic_held_out_test"]
        test_delta = held_out["accuracy"] - held_out_generic["accuracy"]
        selected_name = (
            selected[0]
            if len(selected) == 1
            else "majority vote: " + ", ".join(selected)
        )
        lines.extend(
            [
                "",
                "## Prompt selection without test-set leakage",
                "",
                f"The first {prompt_selection['development_cases']} class-stratified images were used to compare prompt candidates. "
                f"The remaining {prompt_selection['test_cases']} images were kept hidden from selection.",
                "",
                f"The development set selected **{selected_name}** at "
                f"{development['balanced_accuracy']:.1%} balanced accuracy.",
                f"On the held-out images, that fixed choice scored **{held_out['correct']}/{held_out['attempted']} "
                f"({held_out['accuracy']:.1%})**, compared with **{held_out_generic['correct']}/{held_out_generic['attempted']} "
                f"({held_out_generic['accuracy']:.1%})** for generic {model_name} ({test_delta * 100:+.1f} points).",
                "",
                f"A prompt is considered an improvement only if this held-out result beats generic {model_name}. Development accuracy by itself is not evidence of improvement.",
            ]
        )
    elif result.get("prompt_selection_note"):
        lines.extend(
            [
                "",
                "## Prompt selection",
                "",
                result["prompt_selection_note"],
                "The full-set comparison is descriptive only; it does not select or validate a winning prompt.",
            ]
        )
    performance = result.get("performance", {})
    if performance:
        lines.extend(
            [
                "",
                "## Runtime",
                "",
                f"- Configured batch size: {performance['configured_batch_size']} images",
                f"- Completed batches: {performance['completed_batches']}",
                f"- Total {model_name} inference time: {performance['inference_seconds']:.1f} seconds",
                f"- Mean time per image and prompt strategy: {performance['mean_inference_seconds_per_image_strategy']:.3f} seconds",
            ]
        )
    coverage_gaps = report_context.get("coverage_gaps", [])
    if coverage_gaps:
        lines.extend(
            [
                "",
                "## Coverage gaps",
                "",
                *[f"- {gap}" for gap in coverage_gaps],
            ]
        )
    next_steps = report_context.get(
        "next_steps",
        [
            "Use patient-independent images with documented train/test separation for each label.",
            "Add more tissue groups and disease families.",
            "Fix all image selections before running any prompt version.",
            "Report accuracy for each tissue group, not only one combined number.",
            "Test report writing separately with a rubric for factual support, missing findings, citations, and unsupported claims.",
        ],
    )
    lines.extend(
        [
            "",
            "## Reproducibility and sample size",
            "",
            sample_note,
            "",
            source_note,
            "",
            "## What a broader benchmark should add",
            "",
            *[f"- {item}" for item in next_steps],
            "",
            "## Limits",
            "",
            f"- This is a {len(result['cases'])}-image engineering benchmark, not a clinical validation study.",
            f"- {source_note}",
            "- Results measure only the candidate-label task defined by the manifest, not unrestricted diagnosis.",
            "- The hosted hackathon API returns only the winning label and one score. Scores from tasks with different candidate-set sizes are not directly comparable; calibration, margins, and rank changes cannot be measured.",
            "- Prompts are fixed before inference and do not receive the image, report, or ground-truth label.",
            "- Results may vary when the remote model, preprocessing, or Lumen model changes.",
            "",
            f"Run ID: `{result['run_id']}`",
            "",
        ]
    )
    return "\n".join(lines)
