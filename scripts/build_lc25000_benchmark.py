#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SOURCE_URL = "https://huggingface.co/datasets/1aurent/LC25000"
SOURCE_COMMIT = "2387ffed63932faa8fd05c679ffec85fc3153f61"
SAMPLE_EVERY = 25
SAMPLES_PER_CLASS = 200

CLASSES = {
    (0, 0): ("benign-lung", "lung histopathology", "benign lung tissue"),
    (0, 1): ("lung-adenocarcinoma", "lung histopathology", "lung adenocarcinoma"),
    (0, 2): (
        "lung-squamous-cell-carcinoma",
        "lung histopathology",
        "lung squamous cell carcinoma",
    ),
    (1, 0): ("benign-colon", "colon histopathology", "benign colonic tissue"),
    (1, 1): (
        "colorectal-adenocarcinoma",
        "colon histopathology",
        "colorectal adenocarcinoma",
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the fixed 1,000-image LC25000 benchmark from Parquet shards."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=ROOT / ".benchmark-cache" / "lc25000-parquet" / "data",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "benchmarks" / "lc25000-1000",
    )
    args = parser.parse_args()

    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit("Run with: uv run --with pyarrow python scripts/build_lc25000_benchmark.py") from exc

    source_files = sorted(args.source_dir.glob("*.parquet"))
    if len(source_files) != 4:
        raise SystemExit(f"Expected four LC25000 Parquet shards, found {len(source_files)}.")

    base_manifest = json.loads((ROOT / "benchmarks" / "manifest.json").read_text())
    families = {
        family: base_manifest["families"][family]
        for family in ("lung histopathology", "colon histopathology")
    }
    selected: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    class_ranks: dict[tuple[int, int], int] = defaultdict(int)
    global_row = 0

    for source_file in source_files:
        parquet = pq.ParquetFile(source_file)
        shard_row = 0
        for batch in parquet.iter_batches(batch_size=256, columns=["image", "organ", "label"]):
            for item in batch.to_pylist():
                key = (int(item["organ"]), int(item["label"]))
                rank = class_ranks[key]
                if rank % SAMPLE_EVERY == 0 and len(selected[key]) < SAMPLES_PER_CLASS:
                    slug, family, ground_truth = CLASSES[key]
                    raw = item["image"]["bytes"]
                    source_name = Path(item["image"]["path"]).name
                    output_path = args.output_dir / "images" / slug / f"{rank:04d}-{source_name}"
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(raw)
                    selected[key].append(
                        {
                            "id": f"lc25000-{slug}-rank-{rank}",
                            "image_path": str(output_path.relative_to(ROOT)),
                            "sha256": hashlib.sha256(raw).hexdigest(),
                            "dataset_global_row": global_row,
                            "class_rank": rank,
                            "source_name": source_name,
                            "source_shard": source_file.name,
                            "source_shard_row": shard_row,
                            "family": family,
                            "ground_truth": ground_truth,
                        }
                    )
                class_ranks[key] += 1
                global_row += 1
                shard_row += 1

    if set(selected) != set(CLASSES):
        raise SystemExit("The source dataset did not contain every expected LC25000 class.")
    if any(len(images) != SAMPLES_PER_CLASS for images in selected.values()):
        counts = {str(key): len(images) for key, images in selected.items()}
        raise SystemExit(f"Expected 200 images per class, got {counts}.")

    case_sets = []
    checksum_lines = []
    for key, (slug, family, ground_truth) in CLASSES.items():
        images = selected[key]
        case_sets.append(
            {
                "id_prefix": f"lc25000-{slug}",
                "family": family,
                "ground_truth": ground_truth,
                "source_url": SOURCE_URL,
                "source_note": (
                    f"Every {SAMPLE_EVERY}th class row from LC25000 commit {SOURCE_COMMIT}, "
                    "selected before model inference."
                ),
                "source_license": "Unlicense",
                "images": [
                    {key: value for key, value in image.items() if key not in {"family", "ground_truth"}}
                    for image in images
                ],
            }
        )
        checksum_lines.extend(
            f"{image['sha256']}  {image['image_path']}" for image in images
        )

    manifest = {
        "name": "HistoPrompt LC25000 1,000-image benchmark",
        "version": 1,
        "report_context": {
            "sample_note": (
                "This run stores 1,000 exact image files and verifies every SHA-256 checksum "
                "before inference. It uses 200 deterministic samples from each of five classes."
            ),
            "source_note": (
                "All images come from LC25000. The dataset contains augmented derivatives of a "
                "smaller original collection, so samples are not patient-independent."
            ),
        },
        "families": families,
        "case_sets": case_sets,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "checksums.sha256").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )
    lung_output_dir = ROOT / "benchmarks" / "lc25000-600"
    lung_case_sets = [
        case_set for case_set in case_sets if case_set["family"] == "lung histopathology"
    ]
    lung_manifest = {
        "name": "HistoPrompt LC25000 600-image lung benchmark",
        "version": 1,
        "report_context": {
            "sample_note": (
                "This run uses 600 exact image files and verifies every SHA-256 checksum "
                "before inference. It contains 200 deterministic samples from each lung class."
            ),
            "source_note": (
                "All images come from the lung portion of LC25000. The dataset contains "
                "augmented derivatives of a smaller original collection, so samples are not "
                "patient-independent."
            ),
        },
        "families": {"lung histopathology": families["lung histopathology"]},
        "case_sets": lung_case_sets,
    }
    lung_output_dir.mkdir(parents=True, exist_ok=True)
    (lung_output_dir / "manifest.json").write_text(
        json.dumps(lung_manifest, indent=2) + "\n", encoding="utf-8"
    )
    lung_checksums = [
        f"{image['sha256']}  {image['image_path']}"
        for case_set in lung_case_sets
        for image in case_set["images"]
    ]
    (lung_output_dir / "checksums.sha256").write_text(
        "\n".join(lung_checksums) + "\n", encoding="utf-8"
    )
    print(f"Wrote {sum(map(len, selected.values()))} images to {args.output_dir}.")


if __name__ == "__main__":
    main()
