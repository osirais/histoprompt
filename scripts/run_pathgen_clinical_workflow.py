#!/usr/bin/env python3
"""Run every PathGen case through the clinician-style HistoPrompt workflow."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from histoprompt.clinical_workflow import (  # noqa: E402
    PROMPT_BUILDER_SYSTEM,
    REVIEW_SYSTEM_PROMPT,
    build_prompt_generation_request,
    build_review_request,
    format_evidence,
    generic_prompt,
    json_from_model,
    normalize_review_classification,
    parse_lumen_prompts,
)
from histoprompt.config import Settings  # noqa: E402
from histoprompt.hosted_backend import (  # noqa: E402
    MODEL_NAMES,
    make_benchmark_backend,
)
from histoprompt.lumen import LumenClient  # noqa: E402
from histoprompt.pathgen_benchmark import (  # noqa: E402
    PROJECT_LABELS,
    sha256_file,
    strip_png_metadata,
)
from histoprompt.pathgen_workflow import (  # noqa: E402
    select_cases,
    summarize_workflow,
)
from histoprompt.rag import EvidenceIndex  # noqa: E402


DEFAULT_IMAGE_DIR = Path(
    "/projects/bfqi/shared/datasets/pathgen_dataset/pathgen_2k_output"
)
DEFAULT_OUTPUT_DIR = ROOT / "benchmarks" / "pathgen-clinical-workflow"
T = TypeVar("T")


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _verified_text(path: Path, expected_sha256: str) -> str:
    if sha256_file(path) != expected_sha256:
        raise ValueError(f"Checksum mismatch for {path.name}")
    return path.read_text(encoding="utf-8").strip()


def _data_url(path: Path, expected_sha256: str) -> str:
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256:
        raise ValueError(f"Checksum mismatch for {path.name}: {actual}")
    clean = strip_png_metadata(raw)
    return "data:image/png;base64," + base64.b64encode(clean).decode("ascii")


def _retry(description: str, action: Callable[[], T], attempts: int) -> T:
    error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return action()
        except Exception as exc:  # External services expose several error types.
            error = exc
            if attempt < attempts:
                time.sleep(min(2 ** (attempt - 1), 8))
    assert error is not None
    raise RuntimeError(f"{description} failed after {attempts} attempts: {error}") from error


def _top_prediction(predictions: list[Any]) -> dict[str, Any]:
    if not predictions:
        raise RuntimeError("Hosted model returned no predictions.")
    return predictions[0].as_dict()


def _classify_model(
    model: str,
    backend: Any,
    image: str,
    baseline_prompts: dict[str, str],
    enhanced_prompts: dict[str, str],
    attempts: int,
) -> tuple[str, dict[str, Any]]:
    started = time.perf_counter()
    baseline = _retry(
        f"{model} baseline",
        lambda: _top_prediction(backend.classify(image, baseline_prompts)),
        attempts,
    )
    baseline_seconds = time.perf_counter() - started
    started = time.perf_counter()
    enhanced = _retry(
        f"{model} enhanced",
        lambda: _top_prediction(backend.classify(image, enhanced_prompts)),
        attempts,
    )
    return model, {
        "baseline": baseline,
        "enhanced": enhanced,
        "timing_seconds": {
            "baseline": baseline_seconds,
            "enhanced": time.perf_counter() - started,
        },
    }


def _process_case(
    *,
    case: dict[str, Any],
    image_dir: Path,
    labels: list[str],
    evidence_index: EvidenceIndex,
    lumen: LumenClient,
    backends: dict[str, Any],
    manifest_sha256: str,
    workflow_sha256: str,
    top_k: int,
    attempts: int,
) -> dict[str, Any]:
    case_started = time.perf_counter()
    report = _verified_text(
        image_dir / str(case["caption_file"]), str(case["caption_sha256"])
    )
    image = _data_url(
        image_dir / str(case["image_file"]), str(case["image_sha256"])
    )
    evidence = evidence_index.search(" ".join([report, *labels]), top_k)
    evidence_text = format_evidence(evidence)
    prompt_request = build_prompt_generation_request(report, labels, evidence_text)

    started = time.perf_counter()
    raw_prompt_plan, prompt_model = _retry(
        "Lumen prompt generation",
        lambda: lumen.complete(PROMPT_BUILDER_SYSTEM, prompt_request),
        attempts,
    )
    prompt_seconds = time.perf_counter() - started
    enhanced_prompts, parsed_prompt_plan = parse_lumen_prompts(
        raw_prompt_plan, labels
    )
    baseline_prompts = {label: generic_prompt(label) for label in labels}

    model_results: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=len(backends)) as model_pool:
        futures = [
            model_pool.submit(
                _classify_model,
                model,
                backend,
                image,
                baseline_prompts,
                enhanced_prompts,
                attempts,
            )
            for model, backend in backends.items()
        ]
        for future in as_completed(futures):
            model, result = future.result()
            model_results[model] = result
    model_results = {model: model_results[model] for model in backends}

    review_request = build_review_request(
        report=report,
        labels=labels,
        prompts=enhanced_prompts,
        model_results=model_results,
        evidence_text=evidence_text,
    )
    started = time.perf_counter()
    raw_review, review_model = _retry(
        "Lumen evidence review",
        lambda: lumen.complete(REVIEW_SYSTEM_PROMPT, review_request, prompt_model),
        attempts,
    )
    review_seconds = time.perf_counter() - started
    review = json_from_model(raw_review)

    return {
        "schema_version": 1,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": manifest_sha256,
        "workflow_sha256": workflow_sha256,
        "case_id": case["case_id"],
        "wsi_id": case["wsi_id"],
        "participant_id": case["participant_id"],
        "project_id": case["project_id"],
        "ground_truth": case["ground_truth"],
        "image_file": case["image_file"],
        "image_sha256": case["image_sha256"],
        "report_source": "PathGen generated caption used as a simulated case report",
        "report_file": case["caption_file"],
        "report_sha256": case["caption_sha256"],
        "report": report,
        "candidate_labels": labels,
        "evidence": [item.as_dict() for item in evidence],
        "prompt_generation_request": prompt_request,
        "raw_prompt_plan": raw_prompt_plan,
        "parsed_prompt_plan": parsed_prompt_plan,
        "baseline_prompts": baseline_prompts,
        "enhanced_prompts": enhanced_prompts,
        "model_results": model_results,
        "review_request": review_request,
        "raw_review": raw_review if review is None else "",
        "review": review,
        "final_classification": normalize_review_classification(review, labels),
        "lumen_models": {
            "prompt_generation": prompt_model,
            "review": review_model,
        },
        "timing_seconds": {
            "prompt_generation": prompt_seconds,
            "review": review_seconds,
            "total": time.perf_counter() - case_started,
        },
        "notice": "Research prototype only. Not validated for clinical use or patient care.",
    }


def _resume_result(
    path: Path,
    case: dict[str, Any],
    manifest_sha256: str,
    workflow_sha256: str,
    models: list[str],
) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if (
        result.get("case_id") != case["case_id"]
        or result.get("manifest_sha256") != manifest_sha256
        or result.get("workflow_sha256") != workflow_sha256
        or list(result.get("model_results", {})) != models
        or not result.get("final_classification")
    ):
        return None
    return result


def _render_report(
    summary: dict[str, Any], models: list[str], elapsed_seconds: float
) -> str:
    lines = [
        "# PathGen clinician-workflow benchmark",
        "",
        f"Completed cases: **{summary['cases']:,}**",
        "",
        "Each case followed the same path: image plus simulated report and all eight candidate labels, local evidence retrieval, Lumen case-specific prompt generation, all configured pathology image models, and a final Lumen evidence review.",
        "",
        "## Accuracy by decision layer",
        "",
        "| Model or review layer | Image-only baseline | Case-specific prompts | Change | Fixed / broken |",
        "|---|---:|---:|---:|---:|",
    ]
    for model in models:
        result = summary["models"][model]
        before = result["baseline"]
        after = result["enhanced"]
        delta = (after["accuracy"] - before["accuracy"]) * 100
        paired = result["paired"]
        lines.append(
            f"| {MODEL_NAMES[model]} | {before['correct']:,}/{before['total']:,} ({before['accuracy']:.1%}) | "
            f"{after['correct']:,}/{after['total']:,} ({after['accuracy']:.1%}) | "
            f"{delta:+.1f} points | {paired['fixed']} / {paired['broken']} |"
        )
    final = summary["final_review"]
    lines += [
        f"| Final Lumen review | — | {final['correct']:,}/{final['total']:,} ({final['accuracy']:.1%}) | — | — |",
        "",
        "## Change by organ and model",
        "",
        "Positive values mean that case-specific prompts improved accuracy. Negative values mean that they reduced accuracy. Each value is the percentage-point change from the image-only baseline.",
        "",
        "| Organ and disease | Cases | "
        + " | ".join(MODEL_NAMES[model] for model in models)
        + " |",
        "|---|---:|" + "---:|" * len(models),
    ]
    projects = list(final["per_project"])
    for project in projects:
        cells = []
        for model in models:
            before = summary["models"][model]["baseline"]["per_project"][project]
            after = summary["models"][model]["enhanced"]["per_project"][project]
            cells.append(f"{(after['accuracy'] - before['accuracy']) * 100:+.1f}")
        label = PROJECT_LABELS.get(project, project)
        lines.append(
            f"| {label.capitalize()} ({project}) | {final['per_project'][project]['total']:,} | "
            + " | ".join(cells)
            + " |"
        )

    lines += [
        "",
        "## Detailed results by model and organ",
        "",
        "A fixed case was wrong with the image-only prompt and correct with the case-specific prompt. A broken case changed in the opposite direction.",
    ]
    for model in models:
        model_result = summary["models"][model]
        lines += [
            "",
            f"### {MODEL_NAMES[model]}",
            "",
            "| Organ and disease | Cases | Image-only baseline | Case-specific prompts | Change | Fixed / broken |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for project in projects:
            before = model_result["baseline"]["per_project"][project]
            after = model_result["enhanced"]["per_project"][project]
            paired = model_result["paired"]["per_project"][project]
            delta = (after["accuracy"] - before["accuracy"]) * 100
            label = PROJECT_LABELS.get(project, project)
            lines.append(
                f"| {label.capitalize()} ({project}) | {before['total']:,} | "
                f"{before['correct']:,}/{before['total']:,} ({before['accuracy']:.1%}) | "
                f"{after['correct']:,}/{after['total']:,} ({after['accuracy']:.1%}) | "
                f"{delta:+.1f} points | {paired['fixed']:,} / {paired['broken']:,} |"
            )

    lines += [
        "",
        "## Final-review accuracy by organ",
        "",
        "| Organ and disease | Correct | Accuracy |",
        "|---|---:|---:|",
    ]
    for project, result in final["per_project"].items():
        label = PROJECT_LABELS.get(project, project)
        lines.append(
            f"| {label.capitalize()} ({project}) | {result['correct']:,}/{result['total']:,} | {result['accuracy']:.1%} |"
        )
    lines += [
        "",
        f"Wall time: **{elapsed_seconds / 60:.1f} minutes**.",
        "",
        "The simulated reports are PathGen-generated captions, not authentic clinician reports. Some explicitly name an organ or suspected diagnosis, so final-review accuracy and image-model accuracy are reported separately.",
        "",
    ]
    return "\n".join(lines)


def _regenerate_report_only(
    output_dir: Path, manifest: dict[str, Any], manifest_sha256: str
) -> int:
    artifact_path = output_dir / "results.json"
    if not artifact_path.exists():
        raise SystemExit(f"Cannot render report: {artifact_path} does not exist.")
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    if artifact.get("manifest_sha256") != manifest_sha256:
        raise SystemExit("Cannot render report: manifest checksum does not match results.")

    models = [str(model) for model in artifact["models"]]
    workflow_sha256 = str(artifact["workflow_sha256"])
    expected_cases = int(artifact["coverage"]["selected_cases"])
    case_dir = output_dir / "cases"
    selected: list[dict[str, Any]] = []
    saved_results: list[dict[str, Any]] = []
    for case in manifest["cases"]:
        result = _resume_result(
            case_dir / f"{case['case_id']}.json",
            case,
            manifest_sha256,
            workflow_sha256,
            models,
        )
        if result is not None:
            selected.append(case)
            saved_results.append(result)
    if len(saved_results) != expected_cases:
        raise SystemExit(
            "Cannot render report: found "
            f"{len(saved_results):,} matching case records, expected {expected_cases:,}."
        )

    summary = summarize_workflow(selected, saved_results, models)
    artifact["summary"] = summary
    _write_json_atomic(artifact_path, artifact)
    report_path = output_dir / "RESULTS.md"
    report_path.write_text(
        _render_report(summary, models, float(artifact["wall_time_seconds"])),
        encoding="utf-8",
    )
    print(report_path)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "benchmarks" / "pathgen-ncsa" / "manifest.json",
    )
    parser.add_argument("--image-dir", type=Path, default=DEFAULT_IMAGE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--models", nargs="+", choices=sorted(MODEL_NAMES), default=sorted(MODEL_NAMES)
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--per-project", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Regenerate results.json summaries and RESULTS.md from saved case records.",
    )
    args = parser.parse_args()
    if args.workers < 1 or args.attempts < 1 or args.top_k < 1:
        parser.error("workers, attempts, and top-k must be positive")

    started = time.perf_counter()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not manifest.get("coverage", {}).get("complete"):
        raise SystemExit("PathGen manifest is not marked complete.")
    manifest_sha256 = sha256_file(args.manifest)
    if args.report_only:
        return _regenerate_report_only(
            args.output_dir, manifest, manifest_sha256
        )
    selected = select_cases(
        manifest["cases"], per_project=args.per_project, limit=args.limit
    )
    if not selected:
        raise SystemExit("No PathGen cases were selected.")
    labels = list(manifest["labels"].values())
    models = list(dict.fromkeys(args.models))
    settings = Settings.from_env()
    lumen = LumenClient(settings)
    if not lumen.configured:
        raise SystemExit("LUMEN_API_KEY is required for the clinician workflow.")
    evidence_index = EvidenceIndex(settings.corpus_path)
    backends = {model: make_benchmark_backend(settings, model) for model in models}
    source_paths = [
        Path(__file__).resolve(),
        ROOT / "histoprompt" / "clinical_workflow.py",
        ROOT / "histoprompt" / "hosted_backend.py",
        ROOT / "histoprompt" / "lumen.py",
        ROOT / "histoprompt" / "pathgen_benchmark.py",
        ROOT / "histoprompt" / "pathgen_workflow.py",
        ROOT / "histoprompt" / "rag.py",
    ]
    workflow_configuration = {
        "schema_version": 1,
        "candidate_labels": labels,
        "models": models,
        "top_k": args.top_k,
        "lumen_model": settings.lumen_model,
        "corpus_path": str(settings.corpus_path),
        "corpus_sha256": sha256_file(settings.corpus_path),
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256_file(path) for path in source_paths
        },
    }
    workflow_sha256 = hashlib.sha256(
        json.dumps(workflow_configuration, sort_keys=True).encode("utf-8")
    ).hexdigest()
    case_dir = args.output_dir / "cases"
    case_dir.mkdir(parents=True, exist_ok=True)

    results_by_id: dict[str, dict[str, Any]] = {}
    pending: list[dict[str, Any]] = []
    for case in selected:
        path = case_dir / f"{case['case_id']}.json"
        resumed = (
            _resume_result(
                path, case, manifest_sha256, workflow_sha256, models
            )
            if args.resume
            else None
        )
        if resumed is None:
            pending.append(case)
        else:
            results_by_id[str(case["case_id"])] = resumed

    failures: list[dict[str, str]] = []
    completed = len(results_by_id)
    print(
        f"Selected {len(selected)} cases; resuming {completed}; running {len(pending)}.",
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures: dict[Future[dict[str, Any]], dict[str, Any]] = {
            pool.submit(
                _process_case,
                case=case,
                image_dir=args.image_dir,
                labels=labels,
                evidence_index=evidence_index,
                lumen=lumen,
                backends=backends,
                manifest_sha256=manifest_sha256,
                workflow_sha256=workflow_sha256,
                top_k=args.top_k,
                attempts=args.attempts,
            ): case
            for case in pending
        }
        for future in as_completed(futures):
            case = futures[future]
            case_id = str(case["case_id"])
            try:
                result = future.result()
                _write_json_atomic(case_dir / f"{case_id}.json", result)
                results_by_id[case_id] = result
                completed += 1
                print(
                    f"workflow: {completed}/{len(selected)} ({case['project_id']})",
                    flush=True,
                )
            except Exception as exc:
                failures.append({"case_id": case_id, "error": str(exc)})
                print(f"FAILED {case_id}: {exc}", file=sys.stderr, flush=True)

    if failures:
        _write_json_atomic(args.output_dir / "failures.json", failures)
        raise SystemExit(
            f"{len(failures)} cases failed; rerun with --resume after correcting the errors."
        )

    ordered_results = [results_by_id[str(case["case_id"])] for case in selected]
    summary = summarize_workflow(selected, ordered_results, models)
    elapsed = time.perf_counter() - started
    artifact = {
        "schema_version": 1,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": manifest_sha256,
        "workflow_sha256": workflow_sha256,
        "workflow_configuration": workflow_configuration,
        "report_source": "PathGen generated captions used as simulated case reports",
        "candidate_labels": labels,
        "models": models,
        "coverage": {
            "selected_cases": len(selected),
            "source_cases": manifest["coverage"]["included_cases"],
            "complete_source_coverage": len(selected)
            == manifest["coverage"]["included_cases"],
        },
        "wall_time_seconds": elapsed,
        "summary": summary,
        "case_result_directory": str(case_dir),
    }
    _write_json_atomic(args.output_dir / "results.json", artifact)
    (args.output_dir / "RESULTS.md").write_text(
        _render_report(summary, models, elapsed), encoding="utf-8"
    )
    print(args.output_dir / "RESULTS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
