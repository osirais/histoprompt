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
        outcome = f"The enhanced prompts improved accuracy by {delta:.1%}."
    elif delta < 0:
        outcome = f"The enhanced prompts reduced accuracy by {abs(delta):.1%}."
    else:
        outcome = "The enhanced prompts did not change total accuracy."
    outcome += f" They fixed {improvements} original errors and introduced {regressions} new errors."

    lines = [
        "# HistoPrompt multi-disease benchmark",
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
        f"**{evidence_generated['accuracy']:.1%}** | **{delta:+.1%}** |",
        "",
        "## What we tested",
        "",
        f"This run used {len(result['cases'])} fixed public pathology images. It covered "
        f"{disease_conditions} disease conditions and {len(benign_controls)} benign controls.",
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
            "The test was not lung-only. The table shows the number of images in each clinical group. Sample counts still differ by source, so the combined accuracy must be interpreted carefully.",
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
    for case, baseline, enhanced in comparison_rows:
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
    lines.extend(
        [
            "",
            "## Other prompt versions",
            "",
            "The runner also tested two diagnostic variants. These are secondary results, not the main product comparison.",
            "",
            "| Prompt version | Correct | Accuracy |",
            "|---|---:|---:|",
            f"| Label text only | {result['summary']['label_only']['correct']}/{result['summary']['label_only']['successful']} | {result['summary']['label_only']['accuracy']:.1%} |",
            f"| Hand-written microscopic features | {result['summary']['curated']['correct']}/{result['summary']['curated']['successful']} | {result['summary']['curated']['accuracy']:.1%} |",
            "",
            "These extra variants help separate the effect of retrieval from the effect of adding longer microscopic descriptions.",
            "",
            "## Why sample counts are still small",
            "",
            "The first run used eight images because its goal was to test the full path quickly. This expanded run vendors the exact image bytes in the repository and verifies a SHA-256 checksum before inference.",
            "",
            "The expanded set adds repeated samples for the LC25000 and infectious-esophagitis labels plus a skin-cancer group. Some labels still have only one published example, and selected educational images can be easier than random clinical images.",
            "",
            "## What a broader benchmark should add",
            "",
            "- Use at least 10 to 20 independently selected images for each label.",
            "- Add more tissue groups, such as breast, prostate, and lymph node pathology.",
            "- Fix all image selections before running any prompt version.",
            "- Report accuracy for each tissue group, not only one combined number.",
            "- Test report writing separately with a rubric for factual support, missing findings, citations, and unsupported claims.",
            "",
            "## Limits",
            "",
            f"- This is a {len(result['cases'])}-image engineering benchmark, not a clinical validation study.",
            "- LC25000 images use fixed evenly spaced rows from the public dataset. Infectious-esophagitis and skin-cancer images are published educational figures.",
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
