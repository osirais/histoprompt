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
    verify_image_checksum,
)
from histoprompt.config import Settings  # noqa: E402
from histoprompt.lumen import LumenClient  # noqa: E402
from histoprompt.musk_backend import make_musk_backend  # noqa: E402
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


def classify_batch(musk: Any, images: list[str], prompts: dict[str, str]) -> list[Any]:
    batch_method = getattr(musk, "classify_batch", None)
    if callable(batch_method):
        return batch_method(images, prompts)
    return [musk.classify(image, prompts)[0] for image in images]


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the HistoPrompt multi-disease benchmark.")
    parser.add_argument("--manifest", type=Path, default=ROOT / "benchmarks" / "manifest.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "benchmarks" / "results")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".benchmark-cache")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument(
        "--strategies",
        nargs="+",
        choices=STRATEGIES,
        default=list(STRATEGIES),
    )
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")
    required_strategies = {"generic", "evidence_generated"}
    if not required_strategies.issubset(args.strategies):
        parser.error(
            "--strategies must include generic and evidence_generated for the comparison report"
        )

    manifest_value = json.loads(args.manifest.read_text(encoding="utf-8"))
    cases, families = load_manifest(manifest_value)
    settings = Settings.from_env()
    lumen = LumenClient(settings)
    evidence_index = EvidenceIndex(settings.corpus_path)
    musk = make_musk_backend(settings)

    generated_by_family: dict[str, dict[str, str]] = {}
    evidence_by_family: dict[str, list[dict[str, str | float]]] = {}
    prompt_model = ""
    if "evidence_generated" in args.strategies:
        for family, curated in families.items():
            generated, prompt_model, evidence = generate_evidence_prompts(
                family, curated, evidence_index, lumen, prompt_model
            )
            generated_by_family[family] = generated
            evidence_by_family[family] = evidence
            print(f"Generated evidence prompts for {family}.", flush=True)

    rows: list[dict[str, Any]] = []
    encoded_by_family: dict[str, list[tuple[Any, str]]] = {}
    for case in cases:
        raw, reference = case_image(case, args.cache_dir)
        encoded = image_data_url(raw, reference)
        encoded_by_family.setdefault(case.family, []).append((case, encoded))

    benchmark_started = time.perf_counter()
    total_inference_seconds = 0.0
    completed_batches = 0
    for family, prepared_cases in encoded_by_family.items():
        for strategy in args.strategies:
            prompts = prompts_for_strategy(
                strategy, families[family], generated_by_family.get(family)
            )
            for batch_number, batch in enumerate(chunks(prepared_cases, args.batch_size), 1):
                started = time.perf_counter()
                error = ""
                try:
                    predictions = classify_batch(
                        musk, [encoded for _, encoded in batch], prompts
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
                            "prompts": prompts,
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
                print(
                    f"{family} / {strategy} / batch {batch_number}: "
                    f"{len(batch)} images in {elapsed:.2f}s"
                    f"{f' / {error}' if error else ''}",
                    flush=True,
                )

    now = datetime.now(timezone.utc)
    benchmark_wall_seconds = time.perf_counter() - benchmark_started
    result = {
        "run_id": now.strftime("%Y%m%dT%H%M%SZ"),
        "created_at": now.isoformat(),
        "benchmark_name": manifest_value.get("name", "HistoPrompt benchmark"),
        "report_context": manifest_value.get("report_context", {}),
        "manifest": display_path(args.manifest),
        "lumen_model": prompt_model,
        "musk_backend": settings.musk_backend,
        "musk_endpoint": settings.musk_endpoint,
        "cases": [case.__dict__ for case in cases],
        "evidence_generated_prompts": generated_by_family,
        "retrieved_evidence": evidence_by_family,
        "strategies": args.strategies,
        "performance": {
            "configured_batch_size": args.batch_size,
            "completed_batches": completed_batches,
            "inference_seconds": round(total_inference_seconds, 3),
            "benchmark_wall_seconds": round(benchmark_wall_seconds, 3),
            "mean_inference_seconds_per_image_strategy": round(
                total_inference_seconds / len(rows), 6
            ) if rows else 0.0,
        },
        "results": rows,
        "summary": summarize_results(rows),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "latest.json"
    markdown_path = args.output_dir / "latest.md"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown_report(result), encoding="utf-8")
    print(f"Saved {json_path} and {markdown_path}.")


if __name__ == "__main__":
    main()
