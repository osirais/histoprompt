"""Manifest and reporting helpers for the materialized NCSA PathGen subset."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any


PROJECT_LABELS = {
    "TCGA-BRCA": "breast invasive carcinoma",
    "TCGA-COAD": "colon adenocarcinoma",
    "TCGA-KIRC": "kidney renal clear cell carcinoma",
    "TCGA-LGG": "lower-grade glioma",
    "TCGA-LUAD": "lung adenocarcinoma",
    "TCGA-LUSC": "lung squamous cell carcinoma",
    "TCGA-PRAD": "prostate adenocarcinoma",
    "TCGA-READ": "rectal adenocarcinoma",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def participant_id(wsi_id: str) -> str:
    """Return the TCGA participant barcode from a PathGen WSI identifier."""
    fields = wsi_id.split("-")
    if len(fields) < 3 or fields[0] != "TCGA":
        raise ValueError(f"Unsupported PathGen WSI identifier: {wsi_id}")
    return "-".join(fields[:3])


def case_stem(row: dict[str, Any]) -> str:
    position = row.get("position")
    if not isinstance(position, list) or len(position) != 2:
        raise ValueError("Every PathGen row needs a two-value position.")
    return f"{row['file_id']}_{position[0]}_{position[1]}"


def load_project_map(path: Path) -> dict[str, str]:
    """Load participant-to-project assignments from a frozen PathGen manifest."""
    projects: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            participant = str(row.get("participant_id", ""))
            project = str(row.get("project_id", ""))
            if not participant or not project:
                continue
            previous = projects.setdefault(participant, project)
            if previous != project:
                raise ValueError(
                    f"Participant {participant} maps to both {previous} and {project}."
                )
    return projects


def build_manifest(
    metadata_path: Path,
    image_dir: Path,
    project_manifest_path: Path,
) -> dict[str, Any]:
    """Verify every materialized pair and return a checksum-bound manifest."""
    rows = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("PathGen metadata must be a non-empty JSON list.")
    projects = load_project_map(project_manifest_path)
    expected_stems = [case_stem(row) for row in rows]
    if len(expected_stems) != len(set(expected_stems)):
        raise ValueError("PathGen metadata contains duplicate image coordinates.")

    actual_png = {path.stem for path in image_dir.glob("*.png")}
    actual_txt = {path.stem for path in image_dir.glob("*.txt")}
    expected = set(expected_stems)
    if actual_png != expected or actual_txt != expected:
        details = {
            "missing_png": sorted(expected - actual_png)[:10],
            "extra_png": sorted(actual_png - expected)[:10],
            "missing_txt": sorted(expected - actual_txt)[:10],
            "extra_txt": sorted(actual_txt - expected)[:10],
        }
        raise ValueError(f"Materialized PathGen files do not match metadata: {details}")

    cases = []
    for row, stem in zip(rows, expected_stems):
        wsi_id = str(row["wsi_id"])
        participant = participant_id(wsi_id)
        project = projects.get(participant, "")
        if project not in PROJECT_LABELS:
            raise ValueError(
                "No supported TCGA project label for "
                f"{participant}: {project or 'missing'}"
            )
        caption_path = image_dir / f"{stem}.txt"
        caption = str(row.get("caption", "")).strip()
        if caption_path.read_text(encoding="utf-8").strip() != caption:
            raise ValueError(f"Caption mismatch for {stem}.")
        image_path = image_dir / f"{stem}.png"
        cases.append(
            {
                "case_id": stem,
                "wsi_id": wsi_id,
                "participant_id": participant,
                "project_id": project,
                "ground_truth": PROJECT_LABELS[project],
                "position": [int(value) for value in row["position"]],
                "image_file": image_path.name,
                "image_sha256": sha256_file(image_path),
                "caption_file": caption_path.name,
                "caption_sha256": sha256_file(caption_path),
            }
        )

    project_counts = Counter(case["project_id"] for case in cases)
    slide_counts = Counter(case["wsi_id"] for case in cases)
    return {
        "schema_version": 1,
        "name": "Complete materialized NCSA PathGen tile benchmark",
        "source": {
            "dataset": "PathGen-1.6M",
            "materialized_collection": "PathGen-2k_samples",
            "metadata_path": str(metadata_path),
            "metadata_sha256": sha256_file(metadata_path),
            "project_manifest_path": str(project_manifest_path),
            "project_manifest_sha256": sha256_file(project_manifest_path),
            "image_directory": str(image_dir),
        },
        "coverage": {
            "metadata_rows": len(rows),
            "materialized_pngs": len(actual_png),
            "materialized_captions": len(actual_txt),
            "included_cases": len(cases),
            "slides": len(slide_counts),
            "projects": len(project_counts),
            "complete": len(cases) == len(rows) == len(actual_png) == len(actual_txt),
            "cases_by_project": dict(sorted(project_counts.items())),
            "cases_by_slide": dict(sorted(slide_counts.items())),
        },
        "labels": dict(sorted(PROJECT_LABELS.items())),
        "cases": cases,
    }


def accuracy_summary(
    cases: Sequence[dict[str, Any]], predictions: Sequence[str]
) -> dict[str, Any]:
    if len(cases) != len(predictions) or not cases:
        raise ValueError("Accuracy needs one prediction for every non-empty case.")
    grouped: dict[str, list[bool]] = defaultdict(list)
    by_slide: dict[str, list[bool]] = defaultdict(list)
    confusion: Counter[tuple[str, str]] = Counter()
    correct = 0
    for case, prediction in zip(cases, predictions):
        truth = str(case["ground_truth"])
        is_correct = prediction == truth
        correct += is_correct
        grouped[str(case["project_id"])].append(is_correct)
        by_slide[str(case["wsi_id"])].append(is_correct)
        confusion[(truth, prediction)] += 1
    return {
        "correct": correct,
        "total": len(cases),
        "accuracy": correct / len(cases),
        "macro_project_accuracy": sum(
            sum(values) / len(values) for values in grouped.values()
        )
        / len(grouped),
        "per_project": {
            project: {
                "correct": sum(values),
                "total": len(values),
                "accuracy": sum(values) / len(values),
            }
            for project, values in sorted(grouped.items())
        },
        "per_slide": {
            slide: {
                "correct": sum(values),
                "total": len(values),
                "accuracy": sum(values) / len(values),
            }
            for slide, values in sorted(by_slide.items())
        },
        "confusion": [
            {"truth": truth, "prediction": prediction, "count": count}
            for (truth, prediction), count in sorted(confusion.items())
        ],
    }


def paired_changes(
    cases: Sequence[dict[str, Any]],
    baseline: Sequence[str],
    candidate: Sequence[str],
) -> dict[str, Any]:
    if len(cases) != len(baseline) or len(cases) != len(candidate):
        raise ValueError("Paired comparison needs one result per case.")
    fixed = broken = unchanged_correct = unchanged_wrong = 0
    for case, before, after in zip(cases, baseline, candidate):
        truth = str(case["ground_truth"])
        before_right = before == truth
        after_right = after == truth
        if after_right and not before_right:
            fixed += 1
        elif before_right and not after_right:
            broken += 1
        elif before_right:
            unchanged_correct += 1
        else:
            unchanged_wrong += 1
    return {
        "fixed": fixed,
        "broken": broken,
        "unchanged_correct": unchanged_correct,
        "unchanged_wrong": unchanged_wrong,
    }


def iter_chunks(values: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    if size < 1:
        raise ValueError("Chunk size must be positive.")
    for start in range(0, len(values), size):
        yield values[start : start + size]
