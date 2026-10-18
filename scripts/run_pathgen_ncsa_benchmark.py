#!/usr/bin/env python3
"""Evaluate one hosted model on every materialized NCSA PathGen PNG."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from histoprompt.config import Settings  # noqa: E402
from histoprompt.hosted_backend import MODEL_NAMES, make_benchmark_backend  # noqa: E402
from histoprompt.pathgen_benchmark import (  # noqa: E402
    accuracy_summary,
    iter_chunks,
    paired_changes,
    sha256_file,
    strip_png_metadata,
)
from histoprompt.pipeline import _generic_prompt  # noqa: E402
from histoprompt.prompt_tuning import (  # noqa: E402
    prompts_from_full_tuning,
    template_prompts,
)


DEFAULT_IMAGE_DIR = Path(
    "/projects/bfqi/shared/datasets/pathgen_dataset/pathgen_2k_output"
)


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _data_url(path: Path, expected_sha256: str) -> str:
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256:
        raise ValueError(f"Checksum mismatch for {path.name}: {actual}")
    inference_bytes = strip_png_metadata(raw)
    return "data:image/png;base64," + base64.b64encode(inference_bytes).decode("ascii")


def _render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Complete materialized NCSA PathGen benchmark",
        "",
        f"Model: **{result['model_name']}**",
        f"Cases: **{result['coverage']['included_cases']:,} tiles from "
        f"{result['coverage']['slides']} slides and {result['coverage']['projects']} TCGA projects**",
        f"Selected base template: `{result['selected_template']}`",
        f"Phrase-tuned benchmark labels: **{len(result['phrase_tuned_benchmark_labels'])}/"
        f"{result['coverage']['projects']}**",
        "",
        "## Overall comparison",
        "",
        "| Prompt set | Correct | Tile accuracy | Macro project accuracy | Inference time |",
        "|---|---:|---:|---:|---:|",
    ]
    for strategy in ("original", "selected_template", "fully_tuned"):
        summary = result["summaries"][strategy]
        lines.append(
            f"| {strategy.replace('_', ' ').title()} | {summary['correct']:,}/{summary['total']:,} | "
            f"{summary['accuracy']:.1%} | {summary['macro_project_accuracy']:.1%} | "
            f"{result['timing_seconds'][strategy]:.1f} s |"
        )
    paired = result["paired_comparisons"]["fully_tuned_vs_original"]
    delta = (
        result["summaries"]["fully_tuned"]["accuracy"]
        - result["summaries"]["original"]["accuracy"]
    )
    lines += [
        "",
        f"The fully tuned prompts changed accuracy by **{delta * 100:+.1f} percentage points**: "
        f"{paired['fixed']} tiles fixed and {paired['broken']} broken.",
        "",
        "## Per-project results",
        "",
        "| TCGA project | Tiles | Original | Selected base | Fully tuned | Tuned vs original |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    original = result["summaries"]["original"]["per_project"]
    selected = result["summaries"]["selected_template"]["per_project"]
    tuned = result["summaries"]["fully_tuned"]["per_project"]
    for project in sorted(original):
        before = original[project]
        base = selected[project]
        after = tuned[project]
        lines.append(
            f"| {project} | {before['total']:,} | {before['accuracy']:.1%} | "
            f"{base['accuracy']:.1%} | {after['accuracy']:.1%} | "
            f"{(after['accuracy'] - before['accuracy']) * 100:+.1f} points |"
        )
    lines += [
        "",
        "## Interpretation boundary",
        "",
        "This run includes every PNG in the materialized NCSA PathGen collection. It is a tile-level engineering "
        "benchmark, not a patient-level clinical validation: the 2,141 tiles come from only 10 whole slides, and "
        "PathGen captions are generated auxiliary text rather than expert ground truth. Ground truth here is the "
        "TCGA cancer-project assignment recorded independently in the frozen full-PathGen manifest.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "benchmarks" / "pathgen-ncsa" / "manifest.json",
    )
    parser.add_argument("--image-dir", type=Path, default=DEFAULT_IMAGE_DIR)
    parser.add_argument("--model", choices=sorted(MODEL_NAMES), required=True)
    parser.add_argument("--template-result", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    if args.template_result is None:
        args.template_result = (
            ROOT
            / "benchmarks"
            / "lc25000-tuning"
            / "results"
            / "full-tuning"
            / f"{args.model}.json"
        )
    if args.output_dir is None:
        args.output_dir = ROOT / "benchmarks" / "pathgen-ncsa" / "results" / args.model

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not manifest.get("coverage", {}).get("complete"):
        raise SystemExit("PathGen manifest is not marked complete.")
    cases = manifest.get("cases", [])
    if len(cases) != manifest["coverage"]["included_cases"]:
        raise SystemExit("PathGen manifest case count does not match its coverage receipt.")
    template_result = json.loads(args.template_result.read_text(encoding="utf-8"))
    if template_result.get("model") != args.model:
        raise SystemExit("Template-selection result belongs to a different model.")
    selected_template = str(template_result["base_template"])
    labels = list(manifest["labels"].values())
    try:
        fully_tuned_prompts, tuned_labels = prompts_from_full_tuning(
            labels, template_result
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    prompts = {
        "original": {label: _generic_prompt(label) for label in labels},
        "selected_template": template_prompts(labels, base=selected_template),
        "fully_tuned": fully_tuned_prompts,
    }

    settings = Settings.from_env()
    backend = make_benchmark_backend(settings, args.model)
    progress_path = args.output_dir / "progress.json"
    progress: dict[str, Any] = {
        "model": args.model,
        "manifest_sha256": sha256_file(args.manifest),
        "template_result_sha256": sha256_file(args.template_result),
        "predictions": {strategy: [] for strategy in prompts},
        "scores": {strategy: [] for strategy in prompts},
        "timing_seconds": {strategy: 0.0 for strategy in prompts},
    }
    if args.resume and progress_path.exists():
        saved = json.loads(progress_path.read_text(encoding="utf-8"))
        if (
            saved.get("model") != progress["model"]
            or saved.get("manifest_sha256") != progress["manifest_sha256"]
            or saved.get("template_result_sha256")
            != progress["template_result_sha256"]
        ):
            raise SystemExit("Saved progress does not match this benchmark configuration.")
        progress = saved

    for strategy, strategy_prompts in prompts.items():
        predictions = progress["predictions"][strategy]
        scores = progress["scores"][strategy]
        if len(predictions) != len(scores) or len(predictions) > len(cases):
            raise SystemExit(f"Invalid saved progress for {strategy}.")
        remaining = cases[len(predictions) :]
        for batch in iter_chunks(remaining, args.batch_size):
            images = [
                _data_url(
                    args.image_dir / case["image_file"], case["image_sha256"]
                )
                for case in batch
            ]
            started = time.perf_counter()
            results = backend.classify_batch(images, strategy_prompts)
            elapsed = time.perf_counter() - started
            if len(results) != len(batch):
                raise RuntimeError(
                    f"{args.model} returned {len(results)} results for {len(batch)} images."
                )
            predictions.extend(result.label for result in results)
            scores.extend(result.probability for result in results)
            progress["timing_seconds"][strategy] += elapsed
            _write_json_atomic(progress_path, progress)
            print(
                f"{args.model} {strategy}: {len(predictions)}/{len(cases)}",
                flush=True,
            )

    summaries = {
        strategy: accuracy_summary(cases, progress["predictions"][strategy])
        for strategy in prompts
    }
    result = {
        "schema_version": 2,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "model_name": MODEL_NAMES[args.model],
        "manifest_sha256": progress["manifest_sha256"],
        "template_result_sha256": progress["template_result_sha256"],
        "selected_template": selected_template,
        "accepted_phrases": {
            label: template_result["chosen_phrases"][label]
            for label in tuned_labels
        },
        "phrase_tuned_benchmark_labels": tuned_labels,
        "untuned_benchmark_labels": sorted(set(labels) - set(tuned_labels)),
        "image_preprocessing": (
            "Verify the original PNG SHA-256, then remove EXIF, ICC, and text metadata "
            "chunks without changing compressed pixel data."
        ),
        "coverage": manifest["coverage"],
        "prompts": prompts,
        "timing_seconds": progress["timing_seconds"],
        "summaries": summaries,
        "paired_changes": paired_changes(
            cases,
            progress["predictions"]["original"],
            progress["predictions"]["fully_tuned"],
        ),
        "paired_comparisons": {
            "selected_template_vs_original": paired_changes(
                cases,
                progress["predictions"]["original"],
                progress["predictions"]["selected_template"],
            ),
            "fully_tuned_vs_original": paired_changes(
                cases,
                progress["predictions"]["original"],
                progress["predictions"]["fully_tuned"],
            ),
            "fully_tuned_vs_selected_template": paired_changes(
                cases,
                progress["predictions"]["selected_template"],
                progress["predictions"]["fully_tuned"],
            ),
        },
        "predictions": [
            {
                "case_id": case["case_id"],
                "wsi_id": case["wsi_id"],
                "project_id": case["project_id"],
                "ground_truth": case["ground_truth"],
                "original": progress["predictions"]["original"][index],
                "original_score": progress["scores"]["original"][index],
                "selected_template": progress["predictions"]["selected_template"][index],
                "selected_template_score": progress["scores"]["selected_template"][index],
                "fully_tuned": progress["predictions"]["fully_tuned"][index],
                "fully_tuned_score": progress["scores"]["fully_tuned"][index],
            }
            for index, case in enumerate(cases)
        ],
    }
    _write_json_atomic(args.output_dir / "latest.json", result)
    (args.output_dir / "latest.md").write_text(
        _render_report(result), encoding="utf-8"
    )
    print(f"Saved {args.output_dir / 'latest.json'} and latest.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
