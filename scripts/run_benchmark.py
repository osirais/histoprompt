#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from histoprompt.benchmark import (  # noqa: E402
    STRATEGIES,
    generate_evidence_prompts,
    load_manifest,
    prompts_for_strategy,
    summarize_results,
    supports_prompt_selection,
    verify_image_checksum,
)
from histoprompt.config import Settings  # noqa: E402
from histoprompt.hosted_backend import (  # noqa: E402
    MODEL_NAMES,
    make_benchmark_backend,
)
from histoprompt.lumen import LumenClient  # noqa: E402
from histoprompt.prompt_selection import select_prompt_candidate  # noqa: E402
from histoprompt.reporting import markdown_report  # noqa: E402
from histoprompt.rag import EvidenceIndex  # noqa: E402


def download_image(url: str, destination: Path) -> bytes:
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(url, headers={"User-Agent": "HistoPrompt benchmark/0.1"})
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
        destination.write_bytes(raw)
    return destination.read_bytes()


def image_data_url(raw: bytes, url: str) -> str:
    media_type = mimetypes.guess_type(url)[0] or "image/jpeg"
    return f"data:{media_type};base64,{base64.b64encode(raw).decode('ascii')}"


def case_image(case: Any, cache_dir: Path) -> tuple[bytes, str]:
    if case.image_path:
        path = ROOT / case.image_path
        raw = path.read_bytes()
        reference = str(path)
    else:
        suffix = Path(urlparse(case.image_url).path).suffix or ".img"
        path = cache_dir / f"{case.case_id}{suffix}"
        raw = download_image(case.image_url, path)
        reference = case.image_url
    verify_image_checksum(raw, case.sha256, case.case_id)
    return raw, reference


def chunks(values: list[Any], size: int) -> list[list[Any]]:
    return [values[start : start + size] for start in range(0, len(values), size)]


def classify_batch(model: Any, images: list[str], prompts: dict[str, str]) -> list[Any]:
    batch_method = getattr(model, "classify_batch", None)
    if callable(batch_method):
        return batch_method(images, prompts)
    return [model.classify(image, prompts)[0] for image in images]


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the HistoPrompt multi-disease benchmark.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "benchmarks" / "diagnosis-11" / "manifest.json",
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--model", choices=sorted(MODEL_NAMES), default="musk")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".benchmark-cache")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument(
        "--max-per-label",
        type=int,
        default=0,
        help="Use only the first N fixed cases per family/label for rapid prompt screening.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Keep completed strategies from output-dir/latest.json and run only the requested strategies.",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Regenerate latest.md from an existing latest.json without calling a model.",
    )
    parser.add_argument(
        "--strategies",
        nargs="+",
        choices=STRATEGIES,
        help="Prompt strategies to run; defaults to the manifest's main comparison.",
    )
    args = parser.parse_args()
    if args.output_dir is None:
        args.output_dir = args.manifest.parent / "results" / args.model
    if args.report_only:
        json_path = args.output_dir / "latest.json"
        if not json_path.exists():
            parser.error(f"Cannot render report: {json_path} does not exist.")
        result = json.loads(json_path.read_text(encoding="utf-8"))
        if args.manifest.exists():
            current_manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
            result["benchmark_name"] = current_manifest.get(
                "name", result.get("benchmark_name", "HistoPrompt benchmark")
            )
            result["comparison"] = current_manifest.get(
                "comparison", result.get("comparison", {})
            )
            result["report_context"] = current_manifest.get(
                "report_context", result.get("report_context", {})
            )
        markdown_path = args.output_dir / "latest.md"
        json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        markdown_path.write_text(markdown_report(result), encoding="utf-8")
        print(f"Saved {markdown_path}.")
        return
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")
    if args.max_per_label < 0:
        parser.error("--max-per-label cannot be negative")
    manifest_value = json.loads(args.manifest.read_text(encoding="utf-8"))
    comparison = dict(manifest_value.get("comparison", {}))
    comparison.setdefault("baseline_strategy", "generic")
    comparison.setdefault("candidate_strategy", "evidence_generated")
    if args.strategies is None:
        args.strategies = [
            comparison["baseline_strategy"],
            comparison["candidate_strategy"],
        ]
    cases, families = load_manifest(manifest_value)
    if args.max_per_label:
        counts: dict[tuple[str, str], int] = {}
        limited_cases = []
        for case in cases:
            key = (case.family, case.ground_truth)
            if counts.get(key, 0) >= args.max_per_label:
                continue
            counts[key] = counts.get(key, 0) + 1
            limited_cases.append(case)
        cases = limited_cases
    settings = Settings.from_env()
    lumen = LumenClient(settings)
    evidence_index = EvidenceIndex(settings.corpus_path)
    model_backend = make_benchmark_backend(settings, args.model)

    previous: dict[str, Any] = {}
    previous_path = args.output_dir / "latest.json"
    if args.resume and previous_path.exists():
        previous = json.loads(previous_path.read_text(encoding="utf-8"))
        expected_case_ids = [case.case_id for case in cases]
        previous_case_ids = [str(case.get("case_id")) for case in previous.get("cases", [])]
        if previous_case_ids != expected_case_ids:
            parser.error("Cannot resume: saved result cases do not match the manifest.")

    generated_by_family: dict[str, dict[str, str]] = {}
    prompt_file_value = manifest_value.get("evidence_generated_prompts_file")
    frozen_prompt_model = ""
    if prompt_file_value:
        prompt_path = args.manifest.parent / str(prompt_file_value)
        frozen_prompt_value = json.loads(prompt_path.read_text(encoding="utf-8"))
        generated_by_family.update(frozen_prompt_value.get("prompts", {}))
        frozen_prompt_model = str(frozen_prompt_value.get("lumen_model", ""))
    generated_by_family.update(previous.get("evidence_generated_prompts", {}))
    evidence_by_family: dict[str, list[dict[str, str | float]]] = dict(
        previous.get("retrieved_evidence", {})
    )
    prompt_model = str(previous.get("lumen_model", frozen_prompt_model))
    needs_generated_prompts = any(
        strategy in {
            "evidence_generated",
            "generic_with_features",
            "generic_with_primary_feature",
        }
        for strategy in args.strategies
    )
    if needs_generated_prompts:
        for family, curated in families.items():
            if family in generated_by_family:
                continue
            generated, prompt_model, evidence = generate_evidence_prompts(
                family, curated, evidence_index, lumen, prompt_model
            )
            generated_by_family[family] = generated
            evidence_by_family[family] = evidence
            print(f"Generated evidence prompts for {family}.", flush=True)

    rerun_strategies = set(args.strategies)
    strategy_prompts: dict[str, dict[str, dict[str, str]]] = dict(
        previous.get("strategy_prompts", {})
    )
    rows: list[dict[str, Any]] = [
        row
        for row in previous.get("results", [])
        if row.get("strategy") not in rerun_strategies
    ]
    encoded_by_family: dict[str, list[tuple[Any, str]]] = {}
    for case in cases:
        raw, reference = case_image(case, args.cache_dir)
        encoded = image_data_url(raw, reference)
        encoded_by_family.setdefault(case.family, []).append((case, encoded))

    benchmark_started = time.perf_counter()
    total_inference_seconds = 0.0
    completed_batches = 0
    new_rows = 0
    for family, prepared_cases in encoded_by_family.items():
        for strategy in args.strategies:
            prompts = prompts_for_strategy(
                strategy, families[family], generated_by_family.get(family)
            )
            strategy_prompts.setdefault(family, {})[strategy] = prompts
            for batch_number, batch in enumerate(chunks(prepared_cases, args.batch_size), 1):
                started = time.perf_counter()
                error = ""
                try:
                    predictions = classify_batch(
                        model_backend, [encoded for _, encoded in batch], prompts
                    )
                except Exception as exc:
                    predictions = [None] * len(batch)
                    error = f"{type(exc).__name__}: {exc}"
                elapsed = time.perf_counter() - started
                total_inference_seconds += elapsed
                completed_batches += 1
                seconds_per_image = elapsed / len(batch)
                for (case, _), prediction in zip(batch, predictions):
                    rows.append(
                        {
                            "case_id": case.case_id,
                            "family": case.family,
                            "ground_truth": case.ground_truth,
                            "strategy": strategy,
                            "prediction": prediction.label if prediction else None,
                            "score": prediction.probability if prediction else None,
                            "correct": bool(
                                prediction and prediction.label == case.ground_truth
                            ),
                            "error": error,
                            "batch_size": len(batch),
                            "batch_seconds": round(elapsed, 6),
                            "seconds_per_image": round(seconds_per_image, 6),
                        }
                    )
                    new_rows += 1
                print(
                    f"{family} / {strategy} / batch {batch_number}: "
                    f"{len(batch)} images in {elapsed:.2f}s"
                    f"{f' / {error}' if error else ''}",
                    flush=True,
                )

    now = datetime.now(timezone.utc)
    benchmark_wall_seconds = time.perf_counter() - benchmark_started
    report_context = dict(manifest_value.get("report_context", {}))
    if args.max_per_label:
        report_context["sample_note"] = (
            f"This rapid screen uses the first {args.max_per_label} fixed images per "
            "family/label and verifies each SHA-256 checksum before inference."
        )
    all_strategies = list(
        dict.fromkeys([*previous.get("strategies", []), *args.strategies])
    )
    required_strategies = {
        comparison["baseline_strategy"],
        comparison["candidate_strategy"],
    }
    if not required_strategies.issubset(all_strategies):
        parser.error(
            "The saved and requested strategies together must include the manifest's "
            "baseline and candidate strategies for the comparison report."
        )
    result = {
        "run_id": now.strftime("%Y%m%dT%H%M%SZ"),
        "created_at": now.isoformat(),
        "benchmark_name": manifest_value.get("name", "HistoPrompt benchmark"),
        "model": args.model,
        "model_display_name": MODEL_NAMES[args.model],
        "comparison": comparison,
        "report_context": report_context,
        "manifest": display_path(args.manifest),
        "max_per_label": args.max_per_label,
        "lumen_model": prompt_model,
        "model_backend": settings.musk_backend if args.model == "musk" else "remote",
        "model_endpoint": getattr(model_backend, "endpoint", "local"),
        "cases": [case.__dict__ for case in cases],
        "evidence_generated_prompts": generated_by_family,
        "retrieved_evidence": evidence_by_family,
        "strategy_prompts": strategy_prompts,
        "strategies": all_strategies,
        "performance": {
            "scope": "latest invocation",
            "configured_batch_size": args.batch_size,
            "completed_batches": completed_batches,
            "inference_seconds": round(total_inference_seconds, 3),
            "benchmark_wall_seconds": round(benchmark_wall_seconds, 3),
            "mean_inference_seconds_per_image_strategy": round(
                total_inference_seconds / new_rows, 6
            ) if new_rows else 0.0,
        },
        "results": rows,
        "summary": summarize_results(rows),
    }
    if supports_prompt_selection(cases):
        result["prompt_selection"] = select_prompt_candidate(
            rows, result["cases"], all_strategies
        )
    else:
        result["prompt_selection_note"] = (
            "Not run because at least one family/label group has fewer than two cases."
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "latest.json"
    markdown_path = args.output_dir / "latest.md"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown_report(result), encoding="utf-8")
    print(f"Saved {json_path} and {markdown_path}.")


if __name__ == "__main__":
    main()
