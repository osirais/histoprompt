#!/usr/bin/env python3
"""Run the complete materialized NCSA PathGen benchmark for all hosted models."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ("musk", "conch", "quiltnet", "plip")


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def _render_summary(results: dict[str, dict]) -> str:
    lines = [
        "# Complete materialized NCSA PathGen benchmark",
        "",
        "Every model was evaluated on all 2,141 materialized PathGen PNGs from 10 slides and 8 TCGA projects. "
        "The selected base template for each model was frozen using separate LC25000 tuning and confirmation sets.",
        "",
        "| Model | Original | Selected template | Change | Fixed / broken | Macro-project selected | Time |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model in MODELS:
        result = results[model]
        original = result["summaries"]["original"]
        selected = result["summaries"]["selected_template"]
        paired = result["paired_changes"]
        elapsed = sum(result["timing_seconds"].values())
        lines.append(
            f"| {result['model_name']} | {original['correct']:,}/{original['total']:,} "
            f"({original['accuracy']:.1%}) | {selected['correct']:,}/{selected['total']:,} "
            f"({selected['accuracy']:.1%}) | "
            f"{(selected['accuracy'] - original['accuracy']) * 100:+.1f} points | "
            f"{paired['fixed']} / {paired['broken']} | "
            f"{selected['macro_project_accuracy']:.1%} | {elapsed / 60:.1f} min |"
        )
    lines += [
        "",
        "## What this measures",
        "",
        "This is an eight-way TCGA cancer-project classification stress test over every PathGen tile that was "
        "physically available in the shared NCSA PathGen collection. It compares each model's original generic "
        "prompt with that model's independently selected base template.",
        "",
        "## Limitations",
        "",
        "- The 2,141 tiles come from only 10 whole slides, so tile-level confidence intervals would overstate the "
        "effective sample size.",
        "- PathGen captions are generated auxiliary text and are not used as labels or model inputs here.",
        "- Ground truth is TCGA project membership. Some distinctions, especially colon versus rectal "
        "adenocarcinoma, are not reliably identifiable from an isolated tile.",
        "- The separate 1,620,876-region PathGen inventory is not a four-model image benchmark because NCSA "
        "currently supplies its raw pixels only for this 2,141-tile collection; the larger shared store contains "
        "precomputed CONCH embeddings.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", choices=MODELS, default=list(MODELS))
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--skip-manifest", action="store_true")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")

    if not args.skip_manifest:
        _run([sys.executable, "scripts/build_pathgen_ncsa_manifest.py"])
    commands = []
    for model in args.models:
        command = [
            sys.executable,
            "scripts/run_pathgen_ncsa_benchmark.py",
            "--model",
            model,
            "--batch-size",
            str(args.batch_size),
        ]
        if args.resume:
            command.append("--resume")
        commands.append(command)
    with ThreadPoolExecutor(max_workers=min(args.workers, len(commands))) as pool:
        list(pool.map(_run, commands))

    if set(args.models) == set(MODELS):
        results = {
            model: json.loads(
                (
                    ROOT
                    / "benchmarks"
                    / "pathgen-ncsa"
                    / "results"
                    / model
                    / "latest.json"
                ).read_text(encoding="utf-8")
            )
            for model in MODELS
        }
        output = ROOT / "benchmarks" / "pathgen-ncsa" / "RESULTS.md"
        output.write_text(_render_summary(results), encoding="utf-8")
        print(f"Saved {output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
