#!/usr/bin/env python3
"""Freeze every materialized NCSA PathGen image/caption pair into a manifest."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from histoprompt.pathgen_benchmark import build_manifest  # noqa: E402


DEFAULT_DATA_ROOT = Path("/projects/bfqi/shared/datasets/pathgen_dataset")
DEFAULT_PROJECT_MANIFEST = Path(
    "/projects/bfqi/osirais/pathcontext/manifests/pathgen-v1-split.csv"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata",
        type=Path,
        default=DEFAULT_DATA_ROOT / "PathGen-2k_samples.json",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=DEFAULT_DATA_ROOT / "pathgen_2k_output",
    )
    parser.add_argument(
        "--project-manifest", type=Path, default=DEFAULT_PROJECT_MANIFEST
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "benchmarks" / "pathgen-ncsa" / "manifest.json",
    )
    args = parser.parse_args()

    manifest = build_manifest(args.metadata, args.image_dir, args.project_manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    coverage = manifest["coverage"]
    print(
        f"Saved {coverage['included_cases']} cases from {coverage['slides']} slides "
        f"and {coverage['projects']} projects to {args.output}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
