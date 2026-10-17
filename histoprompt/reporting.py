from __future__ import annotations

from typing import Any


def markdown_report(result: dict[str, Any]) -> str:
    generic = result["summary"]["generic"]
    evidence_generated = result["summary"]["evidence_generated"]
    delta = evidence_generated["accuracy"] - generic["accuracy"]
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
        baseline = rows_by_key[(case["case_id"], "generic")]
        enhanced = rows_by_key[(case["case_id"], "evidence_generated")]
        if baseline.get("prediction") != enhanced.get("prediction"):
            comparison_rows.append((case, baseline, enhanced))
        if baseline.get("correct") and not enhanced.get("correct"):
            regressions += 1
        elif not baseline.get("correct") and enhanced.get("correct"):
            improvements += 1

    if delta > 0:
        outcome = f"The enhanced prompts improved accuracy by {delta * 100:.1f} percentage points."
    elif delta < 0:
        outcome = f"The enhanced prompts reduced accuracy by {abs(delta) * 100:.1f} percentage points."
    else:
        outcome = "The enhanced prompts did not change total accuracy."
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

    lines = [
        f"# {benchmark_name}",
        "",
        "## Short answer",
        "",
        f"Original MUSK classified {generic['correct']} of {generic['successful']} images correctly. "
        f"Enhanced MUSK classified {evidence_generated['correct']} of "
        f"{evidence_generated['successful']} images correctly.",
        outcome,
        "",
        "| Version | What MUSK received | Correct | Accuracy | Change |",
        "|---|---|---:|---:|---:|",
        f"| **Original MUSK** | Image + generic label descriptions | "
        f"**{generic['correct']}/{generic['successful']}** | **{generic['accuracy']:.1%}** | — |",
        f"| **Enhanced MUSK** | Image + descriptions generated from retrieved evidence | "
        f"**{evidence_generated['correct']}/{evidence_generated['successful']}** | "
        f"**{evidence_generated['accuracy']:.1%}** | **{delta * 100:+.1f} points** |",
        "",
        "## What we tested",
        "",
        f"This run used {len(result['cases'])} fixed public pathology images. It covered "
        f"{disease_conditions} disease conditions and {len(benign_controls)} benign "
        f"{'control' if len(benign_controls) == 1 else 'controls'}.",
        "",
        "| Clinical group | Images | Correct labels represented | Labels MUSK chose between |",
        "|---|---:|---|---|",
    ]
    for family, cases in cases_by_family.items():
        truths = ", ".join(dict.fromkeys(case["ground_truth"] for case in cases))
        first_row = next(
            row for row in result["results"] if row["family"] == family
        )
        candidates = ", ".join(first_row["prompts"])
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
            "| Clinical group | Original MUSK | Enhanced MUSK |",
            "|---|---:|---:|",
        ]
    )
    for family, cases in cases_by_family.items():
        case_ids = {case["case_id"] for case in cases}
        baseline_rows = [
            row for row in result["results"]
            if row["case_id"] in case_ids and row["strategy"] == "generic" and not row.get("error")
        ]
        enhanced_rows = [
            row for row in result["results"]
            if row["case_id"] in case_ids and row["strategy"] == "evidence_generated" and not row.get("error")
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
            "| Correct label | Images | Original MUSK | Enhanced MUSK | Enhanced model's most common error |",
            "|---|---:|---:|---:|---|",
        ]
    )
    label_stats = []
    for label in labels:
        baseline_rows = [
            row for row in result["results"]
            if row["ground_truth"] == label and row["strategy"] == "generic" and not row.get("error")
        ]
        enhanced_rows = [
            row for row in result["results"]
            if row["ground_truth"] == label
            and row["strategy"] == "evidence_generated"
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
                f"The largest decline was for {largest_decline['label']}: Original MUSK got "
                f"{largest_decline['baseline_correct']}/{largest_decline['total']} correct, "
                f"while Enhanced MUSK got {largest_decline['enhanced_correct']}/{largest_decline['total']} correct.",
            ]
        )
        if largest_decline["common_error"]:
            wrong_label, wrong_count = largest_decline["common_error"]
            lines.append(
                f"Enhanced MUSK labeled {wrong_count}/{largest_decline['total']} of these images "
                f"as {wrong_label}."
            )
    lines.extend(
        [
            "",
            "## What original and enhanced mean",
            "",
            "- **Original MUSK:** The model received the image and a generic prompt such as `a histopathology image showing lung adenocarcinoma`.",
            "- **Enhanced MUSK:** HistoPrompt retrieved local evidence. Lumen converted that evidence into microscopic feature descriptions. MUSK received the same image with those longer descriptions.",
            "- The benchmark did not give Lumen the image, a report, or the correct label. This prevented the enhanced path from receiving the answer through its prompt.",
            "",
            "## Cases where the prediction changed",
            "",
            "| Clinical group | Correct label | Original MUSK | Enhanced MUSK | Effect of enhancement |",
            "|---|---|---|---|---|",
        ]
    )
    for case, baseline, enhanced in comparison_rows[:25]:
        baseline_prediction = baseline.get("prediction") or "Error"
        enhanced_prediction = enhanced.get("prediction") or "Error"
        if baseline.get("correct") and enhanced.get("correct"):
            effect = "No change; both correct"
        elif baseline.get("correct") and not enhanced.get("correct"):
            effect = "Worse; changed a correct result to an error"
        elif not baseline.get("correct") and enhanced.get("correct"):
            effect = "Better; fixed an original error"
        else:
            effect = "No accuracy gain; both incorrect"
        lines.append(
            f"| {case['family']} | {case['ground_truth']} | {baseline_prediction} | "
            f"{enhanced_prediction} | {effect} |"
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
                f"{item['accuracy']:.1%} |"
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
                f"({held_out_generic['accuracy']:.1%})** for generic MUSK ({test_delta * 100:+.1f} points).",
                "",
                "A prompt is considered an improvement only if this held-out result beats generic MUSK. Development accuracy by itself is not evidence of improvement.",
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
                f"- Total MUSK inference time: {performance['inference_seconds']:.1f} seconds",
                f"- Mean time per image and prompt strategy: {performance['mean_inference_seconds_per_image_strategy']:.3f} seconds",
            ]
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
            "- Use patient-independent images with documented train/test separation for each label.",
            "- Add more tissue groups, such as breast, prostate, and lymph node pathology.",
            "- Fix all image selections before running any prompt version.",
            "- Report accuracy for each tissue group, not only one combined number.",
            "- Test report writing separately with a rubric for factual support, missing findings, citations, and unsupported claims.",
            "",
            "## Limits",
            "",
            f"- This is a {len(result['cases'])}-image engineering benchmark, not a clinical validation study.",
            f"- {source_note}",
            "- Candidate sets differ by organ family, so the task measures within-family discrimination rather than unrestricted diagnosis.",
            "- The hosted hackathon API returns only the winning label and one score. Scores from two-label and three-label families are not directly comparable; calibration, margins, and rank changes cannot be measured.",
            "- Evidence-generated prompts are created once per family without reports, image contents, or ground-truth labels, preventing answer leakage.",
            "- Results may vary when the remote model, preprocessing, or Lumen model changes.",
            "",
            f"Run ID: `{result['run_id']}`",
            "",
        ]
    )
    return "\n".join(lines)
