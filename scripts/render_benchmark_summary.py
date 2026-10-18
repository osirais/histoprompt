#!/usr/bin/env python3
"""Render the repository-wide benchmark summary from saved JSON results."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "benchmarks" / "RESULTS.md"
MODELS = [
    ("musk", "MUSK"),
    ("conch", "CONCH"),
    ("quiltnet", "QuiltNet-B-32"),
    ("plip", "PLIP"),
]
TUNING_FILES = {
    "musk": "reproduced-main.json",
    "conch": "full-conch.json",
    "quiltnet": "full-quiltnet.json",
    "plip": "full-plip.json",
}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing benchmark result: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def score_text(item: dict[str, Any]) -> str:
    correct = int(item["correct"])
    total = int(item["successful"])
    return f"{correct}/{total} ({correct / total:.1%})"


def diagnosis_group_table(results: dict[str, dict[str, Any]]) -> list[str]:
    first = results[MODELS[0][0]]
    families = list(dict.fromkeys(case["family"] for case in first["cases"]))
    lines = [
        "| Clinical group | Images | MUSK | CONCH | QuiltNet-B-32 | PLIP |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for family in families:
        case_ids = {
            case["case_id"] for case in first["cases"] if case["family"] == family
        }
        counts = []
        total = len(case_ids)
        for slug, _ in MODELS:
            rows = [
                row
                for row in results[slug]["results"]
                if row["strategy"] == "generic"
                and row["case_id"] in case_ids
                and not row.get("error")
            ]
            counts.append(sum(bool(row.get("correct")) for row in rows))
        lines.append(
            f"| {family} | {total} | "
            + " | ".join(f"{count}/{total}" for count in counts)
            + " |"
        )
    return lines


def tuning_table() -> list[str]:
    lines = [
        "| Model | Original generic | Short template | Individually tuned | Tuned vs original | Run time |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    result_root = ROOT / "benchmarks" / "lc25000-tuning" / "results"
    for slug, display in MODELS:
        result = load_json(result_root / TUNING_FILES[slug])
        tests = result["test"]
        original = next(value for key, value in tests.items() if key.startswith("original "))
        short = tests["histology showing {label}"]
        tuned = tests["tuned"]
        total = int(original["n"])
        delta = (int(tuned["correct"]) - int(original["correct"])) / total
        lines.append(
            f"| {display} | {original['correct']}/{total} ({original['correct'] / total:.1%}) | "
            f"{short['correct']}/{total} ({short['correct'] / total:.1%}) | "
            f"{tuned['correct']}/{total} ({tuned['correct'] / total:.1%}) | "
            f"{delta * 100:+.1f} points | {float(result['minutes']):.1f} min |"
        )
    return lines


def main() -> int:
    diagnosis = {
        slug: load_json(
            ROOT / "benchmarks" / "diagnosis-11" / "results" / slug / "latest.json"
        )
        for slug, _ in MODELS
    }
    diagnosis_count = len(diagnosis["musk"]["cases"])
    diagnosis_labels = len(
        {case["ground_truth"] for case in diagnosis["musk"]["cases"]}
    )
    lines = [
        "# Benchmark results",
        "",
        "## Current evidence",
        "",
        f"- **Named-diagnosis smoke test:** {diagnosis_count} images covering {diagnosis_labels} labels in four clinical differentials.",
        "- **Prompt tuning:** independent candidate search, confirmation, and a 450-image held-out lung test for each model.",
        "- **Broad-organ diagnosis/reasoning:** pending PathMMU dataset access.",
        "",
        "The previous PanNuke tissue-origin experiment was removed because it did not match HistoPrompt's diagnosis and reasoning task. The current numbers are useful but do not yet establish performance across pathology.",
        "",
        "## 11-label diagnosis smoke test",
        "",
        "The generic prompt beat the frozen evidence-enriched descriptions for all four models.",
        "",
        "| Model | Generic prompt | Evidence-enriched prompt | Change |",
        "|---|---:|---:|---:|",
    ]
    for slug, display in MODELS:
        result = diagnosis[slug]
        generic = result["summary"]["generic"]
        evidence = result["summary"]["evidence_generated"]
        delta = (int(evidence["correct"]) - int(generic["correct"])) / int(
            generic["successful"]
        )
        lines.append(
            f"| {display} | {score_text(generic)} | {score_text(evidence)} | "
            f"{delta * 100:+.1f} points |"
        )
    lines.extend(
        [
            "",
            "### Generic accuracy by clinical group",
            "",
            *diagnosis_group_table(diagnosis),
            "",
            "The per-model reports and every prediction are under [`diagnosis-11/results/`](diagnosis-11/results/). Several labels have only one or two examples, so this suite is only a smoke test.",
            "",
            "## Model-specific lung prompt tuning",
            "",
            "Each model ran its own candidate search and validation. The table below is the final held-out test; phrases were not shared between models.",
            "",
            *tuning_table(),
            "",
            "CONCH, QuiltNet, and PLIP were launched together and took about 21 minutes of wall-clock time. The earlier MUSK run took about 20 minutes. The per-model minutes above are measured model runtimes, not a sequential wall-clock total.",
            "",
            "The selected phrases and search logs are in [`lc25000-tuning/results/`](lc25000-tuning/results/). “Tuned” means the search found the best candidate that passed its internal gates; it does not guarantee improvement over the original generic prompt.",
            "",
            "## Replacement broad benchmark",
            "",
            "PathMMU is the replacement target because it was designed for pathology image understanding and reasoning across multiple organ systems and pathology specialties. It provides answer options, correct answers, and explanations, which support direct baseline-versus-retrieval comparisons without inventing labels.",
            "",
            "PathMMU is separately gated. MUSK model approval does not grant dataset access. After access is approved, the benchmark will use the official validation/test split and will report overall, organ-system, question-type, and source-subset accuracy.",
            "",
            "## What the current results say",
            "",
            "1. Prompt wording is model-specific. A phrase that helps MUSK can hurt CONCH or QuiltNet.",
            "2. Longer evidence-derived descriptions are not automatically better. They reduced accuracy in every model on the small diagnosis screen.",
            "3. The lung results show that prompt tuning can help, but they cannot be generalized across organs or diseases.",
            "4. A broad conclusion must wait for a benchmark designed for diagnosis and visual reasoning, rather than tissue-origin or segmentation data.",
        ]
    )
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved {OUTPUT}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
