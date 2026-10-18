"""Build tuning / confirmation / test sets for four pathology classification tasks.

    uv run --with pyarrow --with huggingface-hub python benchmarks/multitask-general-template/build_sets.py

Needs the LC25000 shards in .benchmark-cache/lc25000-parquet/data (see benchmarks/lc25000-tuning/HOW_TO_RUN.md) and
the lung tuning images from scripts/build_lc25000_tuning_sets.py. NCT-CRC-HE and PatchCamelyon rows are read
directly from Hugging Face (only the sampled rows). Images go to .benchmark-cache/multitask/images (ignored by Git).
If manifest.json exists, the rebuilt images are checked against it instead of overwriting it.

  lung      LC25000 lung, 3 classes. Tuning/confirmation: subsets of the committed lung tuning sets; test: the
            first 150 per class of the fixed 600-image benchmark.
  colon     LC25000 colon, 2 classes. All three sets from images outside the colon benchmark (ranks divisible by
            25 below 5000), disjoint, seeded.
  crc9      NCT-CRC-HE, 9 tissue classes. Tuning/confirmation from NCT-CRC-HE-100K; test from CRC-VAL-HE-7K, which
            comes from different patients.
  pcam      PatchCamelyon, lymph node metastasis vs normal. Tuning/confirmation from the 'valid' split, test from
            the 'test' split.
Images are written to ./images/<task>/<set>/ and listed with SHA-256 in manifest.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq
from huggingface_hub import HfFileSystem

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
LC = Path(os.getenv("LC25000_PARQUET_DIR", REPO / ".benchmark-cache" / "lc25000-parquet" / "data"))
IMG_ROOT = REPO / ".benchmark-cache" / "multitask"
SEED = 7
fs = HfFileSystem()
manifest: dict = {"tasks": {}}
rng = random.Random(SEED)


def save(task: str, split: str, label: str, raw: bytes, key: str) -> dict:
    ext = ".png" if raw[:4] == b"\x89PNG" else ".tif" if raw[:2] in (b"II", b"MM") else ".jpg"
    path = IMG_ROOT / "images" / task / split / label.replace(" ", "-") / f"{key}{ext}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"image": str(path.relative_to(IMG_ROOT)), "label": label, "key": key, "sha256": hashlib.sha256(raw).hexdigest()}


def add(task: str, labels: list[str], sets: dict[str, list[dict]], source: str) -> None:
    manifest["tasks"][task] = {"labels": labels, "source": source, "sets": sets}
    print(task, {k: len(v) for k, v in sets.items()}, flush=True)


# ---- lung: reuse committed sets ----
lung_labels = ["benign lung tissue", "lung adenocarcinoma", "lung squamous cell carcinoma"]
tm = json.loads((REPO / "benchmarks/lc25000-tuning/manifest.json").read_text())
sets = {}
for split, n in (("tuning", 150), ("confirmation", 150)):
    rows = []
    for lab in lung_labels:
        picked = [r for r in tm["sets"][split] if r["label"] == lab][:n]
        for r in picked:
            raw = (REPO / ".benchmark-cache/lc25000-tuning" / r["image"]).read_bytes()
            rows.append(save("lung", split, lab, raw, f"r{r['class_rank']}"))
    sets[split] = rows
import sys
sys.path.insert(0, str(REPO))
from histoprompt.benchmark import load_manifest  # noqa: E402
cases, _ = load_manifest(json.loads((REPO / "benchmarks/lc25000-600/manifest.json").read_text()))
test = []
for lab in lung_labels:
    for c in [c for c in cases if c.ground_truth == lab][:150]:
        raw = (REPO / c.image_path).read_bytes()
        test.append(save("lung", "test", lab, raw, c.case_id))
sets["test"] = test
add("lung", lung_labels, sets, "LC25000 lung (tuning/confirmation: committed tuning sets; test: 600-image benchmark)")

# ---- colon: LC25000 colon outside the benchmark ----
colon = {(1, 0): "benign colonic tissue", (1, 1): "colon adenocarcinoma"}
pool = defaultdict(list)
rank = defaultdict(int)
for f in sorted(LC.glob("*.parquet")):
    for b in pq.ParquetFile(f).iter_batches(batch_size=512, columns=["image", "organ", "label"]):
        for it in b.to_pylist():
            k = (int(it["organ"]), int(it["label"]))
            r = rank[k]
            rank[k] += 1
            if k in colon and not (r % 25 == 0 and r < 5000):
                pool[k].append((r, it["image"]["bytes"]))
sets = {"tuning": [], "confirmation": [], "test": []}
for k, lab in colon.items():
    picked = rng.sample(pool[k], 600)
    for split, chunk in (("tuning", picked[:200]), ("confirmation", picked[200:400]), ("test", picked[400:])):
        sets[split] += [save("colon", split, lab, raw, f"r{r}") for r, raw in chunk]
add("colon", list(colon.values()), sets, "LC25000 colon, outside the 1000-image benchmark")


# ---- NCT-CRC-HE: 100K for tuning/confirmation, 7K (other patients) for test ----
crc_names = ["adipose tissue", "background", "debris", "lymphocytes", "mucus", "smooth muscle",
             "normal colon mucosa", "cancer-associated stroma", "colorectal adenocarcinoma epithelium"]


def sample_hf(files: list[str], per_class: dict, key_prefix: str, label_map) -> dict:
    """Read only the label column of every file, then fetch only the row groups holding the sampled rows."""
    index = []
    for f in files:
        with fs.open(f, "rb") as fh:
            pf = pq.ParquetFile(fh)
            labels = pf.read(columns=["label"]).column(0).to_pylist()
            sizes = [pf.metadata.row_group(i).num_rows for i in range(pf.metadata.num_row_groups)]
        start = 0
        for g, n in enumerate(sizes):
            for j in range(n):
                index.append((f, g, j, label_map(labels[start + j])))
            start += n
    by = defaultdict(list)
    for item in index:
        by[item[3]].append(item)
    chosen = {lab: rng.sample(by[lab], n) for lab, n in per_class.items()}
    need = defaultdict(list)
    for lab, items in chosen.items():
        for f, g, j, _ in items:
            need[(f, g)].append((j, lab))
    out = defaultdict(list)
    for (f, g), wanted in sorted(need.items()):
        with fs.open(f, "rb") as fh:
            rows = pq.ParquetFile(fh).read_row_group(g, columns=["image"]).column(0).to_pylist()
        for j, lab in wanted:
            out[lab].append((f"{key_prefix}-{Path(f).stem}-g{g}-{j}", rows[j]["bytes"]))
    return out


nct_files = [p for p in fs.ls("datasets/1aurent/NCT-CRC-HE/data", detail=False) if "NCT_CRC_HE_100K-" in p]
val_files = [p for p in fs.ls("datasets/1aurent/NCT-CRC-HE/data", detail=False) if "CRC_VAL_HE_7K" in p]
tr = sample_hf(nct_files, {n: 100 for n in crc_names}, "nct", lambda v: crc_names[v])
te = sample_hf(val_files, {n: 50 for n in crc_names}, "val", lambda v: crc_names[v])
sets = {"tuning": [], "confirmation": [], "test": []}
for lab in crc_names:
    items = tr[lab]
    sets["tuning"] += [save("crc9", "tuning", lab, raw, k) for k, raw in items[:50]]
    sets["confirmation"] += [save("crc9", "confirmation", lab, raw, k) for k, raw in items[50:100]]
    sets["test"] += [save("crc9", "test", lab, raw, k) for k, raw in te[lab]]
add("crc9", crc_names, sets, "NCT-CRC-HE: 100K (tuning/confirmation) and CRC-VAL-HE-7K (test; different patients)")

# ---- PatchCamelyon ----
pcam_names = ["normal lymph node tissue", "lymph node metastasis"]
pmap = lambda v: pcam_names[1] if v else pcam_names[0]  # noqa: E731
pv = [p for p in fs.ls("datasets/1aurent/PatchCamelyon/data", detail=False) if "/valid-" in p]
pt = [p for p in fs.ls("datasets/1aurent/PatchCamelyon/data", detail=False) if "/test-" in p]
tr = sample_hf(pv, {n: 400 for n in pcam_names}, "valid", pmap)
te = sample_hf(pt, {n: 200 for n in pcam_names}, "test", pmap)
sets = {"tuning": [], "confirmation": [], "test": []}
for lab in pcam_names:
    sets["tuning"] += [save("pcam", "tuning", lab, raw, k) for k, raw in tr[lab][:200]]
    sets["confirmation"] += [save("pcam", "confirmation", lab, raw, k) for k, raw in tr[lab][200:400]]
    sets["test"] += [save("pcam", "test", lab, raw, k) for k, raw in te[lab]]
add("pcam", pcam_names, sets, "PatchCamelyon: 'valid' split (tuning/confirmation), 'test' split (test)")

target = HERE / "manifest.json"
if target.exists():
    expected = json.loads(target.read_text())
    for task, spec in expected["tasks"].items():
        for split, rows in spec["sets"].items():
            got = [(r["image"], r["sha256"]) for r in manifest["tasks"][task]["sets"][split]]
            if got != [(r["image"], r["sha256"]) for r in rows]:
                raise SystemExit(f"Rebuilt {task}/{split} does not match {target}.")
    print("verified against manifest.json")
else:
    target.write_text(json.dumps(manifest, indent=1))
    print("wrote manifest.json")
