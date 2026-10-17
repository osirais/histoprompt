#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import sys
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the HistoPrompt multi-disease benchmark.")
    parser.add_argument("--manifest", type=Path, default=ROOT / "benchmarks" / "manifest.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "benchmarks" / "results")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".benchmark-cache")
    args = parser.parse_args()

    manifest_value = json.loads(args.manifest.read_text(encoding="utf-8"))
    cases, families = load_manifest(manifest_value)
    settings = Settings.from_env()
    lumen = LumenClient(settings)
    evidence_index = EvidenceIndex(settings.corpus_path)
    musk = make_musk_backend(settings)

    generated_by_family: dict[str, dict[str, str]] = {}
    evidence_by_family: dict[str, list[dict[str, str | float]]] = {}
    prompt_model = ""
    for family, curated in families.items():
        generated, prompt_model, evidence = generate_evidence_prompts(
            family, curated, evidence_index, lumen, prompt_model
        )
        generated_by_family[family] = generated
        evidence_by_family[family] = evidence
        print(f"Generated evidence prompts for {family}.", flush=True)

    rows: list[dict[str, Any]] = []
    for case in cases:
        raw, reference = case_image(case, args.cache_dir)
        encoded = image_data_url(raw, reference)
        for strategy in STRATEGIES:
            prompts = prompts_for_strategy(
                strategy, families[case.family], generated_by_family[case.family]
            )
            row: dict[str, Any] = {
                "case_id": case.case_id,
                "family": case.family,
                "ground_truth": case.ground_truth,
                "strategy": strategy,
                "prompts": prompts,
                "prediction": None,
                "score": None,
                "correct": False,
                "error": "",
            }
            try:
                prediction = musk.classify(encoded, prompts)[0]
                row.update(
                    prediction=prediction.label,
                    score=prediction.probability,
                    correct=prediction.label == case.ground_truth,
                )
            except Exception as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"
            rows.append(row)
            print(
                f"{case.case_id} / {strategy}: {row['prediction'] or row['error']}"
                f" ({row['score'] if row['score'] is not None else 'n/a'})",
                flush=True,
            )

    now = datetime.now(timezone.utc)
    result = {
        "run_id": now.strftime("%Y%m%dT%H%M%SZ"),
        "created_at": now.isoformat(),
        "manifest": str(args.manifest.relative_to(ROOT)),
        "lumen_model": prompt_model,
        "musk_backend": settings.musk_backend,
        "musk_endpoint": settings.musk_endpoint,
        "cases": [case.__dict__ for case in cases],
        "evidence_generated_prompts": generated_by_family,
        "retrieved_evidence": evidence_by_family,
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
