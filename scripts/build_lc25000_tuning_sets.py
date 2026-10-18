#!/usr/bin/env python3
"""Build the labelled tuning (A) and confirmation (B) lung sets for prompt tuning.

Draws 300 images per lung label for each set from the full LC25000 dataset (same pinned commit as the 600-image
benchmark), excluding every image in that benchmark (class ranks divisible by 25 below 5,000), with a fixed seed.
Images go to .benchmark-cache/lc25000-tuning/ (ignored by Git); the manifest with SHA-256 checksums is committed.

    uv run --with pyarrow python scripts/build_lc25000_tuning_sets.py \
        --source-dir .benchmark-cache/lc25000-parquet/data
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_URL = "https://huggingface.co/datasets/1aurent/LC25000"
SOURCE_COMMIT = "2387ffed63932faa8fd05c679ffec85fc3153f61"
CLASSES = {(0, 0): "benign lung tissue", (0, 1): "lung adenocarcinoma", (0, 2): "lung squamous cell carcinoma"}
BENCHMARK_EVERY, BENCHMARK_PER_CLASS = 25, 200
PER_SET, SEED = 300, 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-dir", type=Path, default=ROOT / ".benchmark-cache" / "lc25000-parquet" / "data")
    parser.add_argument("--image-dir", type=Path, default=ROOT / ".benchmark-cache" / "lc25000-tuning")
    parser.add_argument("--manifest", type=Path, default=ROOT / "benchmarks" / "lc25000-tuning" / "manifest.json")
    args = parser.parse_args()
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit("Run with: uv run --with pyarrow python scripts/build_lc25000_tuning_sets.py") from exc
    shards = sorted(args.source_dir.glob("*.parquet"))
    if len(shards) != 4:
        raise SystemExit(f"Expected four LC25000 Parquet shards in {args.source_dir}, found {len(shards)}.")

    rows: dict[tuple[int, int], list[tuple[int, bytes, str]]] = defaultdict(list)
    ranks: dict[tuple[int, int], int] = defaultdict(int)
    for shard in shards:
        for batch in pq.ParquetFile(shard).iter_batches(batch_size=512, columns=["image", "organ", "label"]):
            for item in batch.to_pylist():
                key = (int(item["organ"]), int(item["label"]))
                rank = ranks[key]
                ranks[key] += 1
                in_benchmark = rank % BENCHMARK_EVERY == 0 and rank < BENCHMARK_EVERY * BENCHMARK_PER_CLASS
                if key in CLASSES and not in_benchmark:
                    rows[key].append((rank, item["image"]["bytes"], Path(item["image"]["path"]).name))

    random.seed(SEED)
    manifest = {"source_url": SOURCE_URL, "source_commit": SOURCE_COMMIT, "per_label_per_set": PER_SET,
                "seed": SEED, "excluded": "the fixed 600-image lung benchmark (class ranks divisible by 25 below 5000)",
                "sets": {"tuning": [], "confirmation": []}}
    for key, label in CLASSES.items():
        picked = random.sample(rows[key], 2 * PER_SET)
        for split, chunk in (("tuning", picked[:PER_SET]), ("confirmation", picked[PER_SET:])):
            for rank, raw, name in chunk:
                path = args.image_dir / split / label.replace(" ", "-") / f"{rank:05d}-{name}"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                manifest["sets"][split].append({
                    "image": str(path.relative_to(args.image_dir)), "label": label, "class_rank": rank,
                    "source_name": name, "sha256": hashlib.sha256(raw).hexdigest(),
                })
    if args.manifest.exists():                       # committed manifest: verify instead of overwriting
        expected = json.loads(args.manifest.read_text(encoding="utf-8"))
        for split in ("tuning", "confirmation"):
            got = [(r["image"], r["sha256"]) for r in manifest["sets"][split]]
            want = [(r["image"], r["sha256"]) for r in expected["sets"][split]]
            if got != want:
                raise SystemExit(f"The rebuilt {split} set does not match {args.manifest}; check the source shards.")
        print(f"Verified all images against {args.manifest}.")
        return 0
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {sum(len(v) for v in manifest['sets'].values())} images to {args.image_dir} and {args.manifest}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
