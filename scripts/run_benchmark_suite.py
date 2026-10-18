#!/usr/bin/env python3
"""Run complete HistoPrompt benchmark suites and refresh the summary report."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MODELS = ("musk", "conch", "quiltnet", "plip")
SUITES = {
    "diagnosis": {
        "manifest": ROOT / "benchmarks" / "diagnosis-11" / "manifest.json",
        "strategies": ("generic", "evidence_generated"),
    },
}


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite", choices=("diagnosis",), default="diagnosis"
    )
    parser.add_argument("--models", nargs="+", choices=MODELS, default=list(MODELS))
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Regenerate per-model and aggregate Markdown from saved JSON.",
    )
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")

    requested_suites = (args.suite,)

    for suite_name in requested_suites:
        suite = SUITES[suite_name]
        for model in args.models:
            command = [
                sys.executable,
                "scripts/run_benchmark.py",
                "--manifest",
                str(suite["manifest"]),
                "--model",
                model,
            ]
            if args.report_only:
                command.append("--report-only")
            else:
                command.extend(
                    [
                        "--batch-size",
                        str(args.batch_size),
                        "--strategies",
                        *suite["strategies"],
                    ]
                )
            run(command)

    run([sys.executable, "scripts/render_benchmark_summary.py"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
