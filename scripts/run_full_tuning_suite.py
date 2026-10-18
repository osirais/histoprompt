#!/usr/bin/env python3
"""Run documented two-stage prompt tuning independently for hosted models."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ("musk", "conch", "quiltnet", "plip")


def _run(model: str, batch_size: int, candidates: int) -> None:
    output = (
        ROOT
        / "benchmarks"
        / "lc25000-tuning"
        / "results"
        / "full-tuning"
        / f"{model}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ)
    environment.setdefault("LUMEN_MAX_TOKENS", "16000")
    subprocess.run(
        [
            sys.executable,
            "scripts/tune_prompts.py",
            "--model",
            model,
            "--batch-size",
            str(batch_size),
            "--candidates",
            str(candidates),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env=environment,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", choices=MODELS, default=list(MODELS))
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--candidates", type=int, default=8)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.batch_size < 1 or args.candidates < 1 or args.workers < 1:
        parser.error("batch size, candidates, and workers must be positive")
    with ThreadPoolExecutor(max_workers=min(args.workers, len(args.models))) as pool:
        list(
            pool.map(
                lambda model: _run(model, args.batch_size, args.candidates),
                args.models,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
