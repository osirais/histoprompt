import csv
import hashlib
import json

import pytest

from histoprompt.pathgen_benchmark import (
    accuracy_summary,
    build_manifest,
    paired_changes,
    participant_id,
    strip_png_metadata,
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def test_build_manifest_requires_and_hashes_every_pair(tmp_path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    row = {
        "wsi_id": "TCGA-AA-0001-01Z-00-DX1.slide",
        "file_id": "file-one",
        "position": [10, 20],
        "caption": "Generated description.",
    }
    metadata = tmp_path / "metadata.json"
    metadata.write_text(json.dumps([row]))
    (image_dir / "file-one_10_20.png").write_bytes(b"png")
    (image_dir / "file-one_10_20.txt").write_text("Generated description.")
    projects = tmp_path / "projects.csv"
    with projects.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["participant_id", "project_id"])
        writer.writeheader()
        writer.writerow({"participant_id": "TCGA-AA-0001", "project_id": "TCGA-COAD"})

    manifest = build_manifest(metadata, image_dir, projects)

    assert manifest["coverage"] == {
        "metadata_rows": 1,
        "materialized_pngs": 1,
        "materialized_captions": 1,
        "included_cases": 1,
        "slides": 1,
        "projects": 1,
        "complete": True,
        "cases_by_project": {"TCGA-COAD": 1},
        "cases_by_slide": {"TCGA-AA-0001-01Z-00-DX1.slide": 1},
    }
    assert manifest["cases"][0]["image_sha256"] == _sha(b"png")
    assert manifest["cases"][0]["ground_truth"] == "colon adenocarcinoma"


def test_build_manifest_rejects_partial_materialization(tmp_path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    metadata = tmp_path / "metadata.json"
    metadata.write_text(
        json.dumps(
            [
                {
                    "wsi_id": "TCGA-AA-0001-01Z-00-DX1.slide",
                    "file_id": "file-one",
                    "position": [10, 20],
                    "caption": "caption",
                }
            ]
        )
    )
    projects = tmp_path / "projects.csv"
    projects.write_text("participant_id,project_id\nTCGA-AA-0001,TCGA-COAD\n")

    with pytest.raises(ValueError, match="do not match metadata"):
        build_manifest(metadata, image_dir, projects)


def test_accuracy_and_paired_summary_are_project_aware():
    cases = [
        {"ground_truth": "a", "project_id": "A", "wsi_id": "slide-1"},
        {"ground_truth": "a", "project_id": "A", "wsi_id": "slide-1"},
        {"ground_truth": "b", "project_id": "B", "wsi_id": "slide-2"},
    ]
    baseline = ["x", "a", "b"]
    candidate = ["a", "x", "b"]

    summary = accuracy_summary(cases, candidate)

    assert summary["correct"] == 2
    assert summary["macro_project_accuracy"] == 0.75
    assert paired_changes(cases, baseline, candidate) == {
        "fixed": 1,
        "broken": 1,
        "unchanged_correct": 1,
        "unchanged_wrong": 0,
    }


def test_participant_id_rejects_non_tcga_names():
    assert participant_id("TCGA-AA-0001-01Z-00-DX1.slide") == "TCGA-AA-0001"
    with pytest.raises(ValueError):
        participant_id("not-tcga")


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return len(payload).to_bytes(4, "big") + kind + payload + b"crc!"


def test_strip_png_metadata_preserves_pixel_chunks():
    signature = b"\x89PNG\r\n\x1a\n"
    header = _png_chunk(b"IHDR", b"header")
    profile = _png_chunk(b"iCCP", b"large compressed profile")
    pixels = _png_chunk(b"IDAT", b"pixels")
    end = _png_chunk(b"IEND", b"")

    assert strip_png_metadata(signature + header + profile + pixels + end) == (
        signature + header + pixels + end
    )


def test_strip_png_metadata_rejects_truncated_png():
    with pytest.raises(ValueError, match="truncated"):
        strip_png_metadata(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00")
