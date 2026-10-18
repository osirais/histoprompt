#!/usr/bin/env python3
"""Tune MUSK lung label prompts with validation (see histoprompt/prompt_tuning.py for the bars): step 0 chooses
the base template from TEMPLATES, step 1 the phrases.

Sets: tuning (900 extra LC25000 images) and confirmation (900 more), built by scripts/build_lc25000_tuning_sets.py;
test = the first 150 images per label of the fixed 600-image benchmark, scored once at the end against the plain
template and the original generic prompt.

    LUMEN_MODEL=gemma-4-31b-it LUMEN_MAX_TOKENS=16000 uv run python scripts/tune_prompts.py \
        --output benchmarks/lc25000-tuning/results/gemma-4-31b-it.json
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from histoprompt.benchmark import load_manifest, verify_image_checksum  # noqa: E402
from histoprompt.config import Settings  # noqa: E402
from histoprompt.lumen import LumenClient  # noqa: E402
from histoprompt.musk_backend import make_musk_backend  # noqa: E402
from histoprompt.pipeline import _generic_prompt  # noqa: E402
from histoprompt.prompt_tuning import (  # noqa: E402
    CANDIDATE_SYSTEM, DEFAULT_TEMPLATE, TEMPLATES, candidate_request, compare, parse_candidates, select_base,
    template_prompts, tune,
)

FAMILY = "lung histopathology"


def data_url(raw: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tuning-manifest", type=Path, default=ROOT / "benchmarks" / "lc25000-tuning" / "manifest.json")
    parser.add_argument("--image-dir", type=Path, default=ROOT / ".benchmark-cache" / "lc25000-tuning")
    parser.add_argument("--benchmark-manifest", type=Path, default=ROOT / "benchmarks" / "lc25000-600" / "manifest.json")
    parser.add_argument("--test-per-label", type=int, default=150)
    parser.add_argument("--candidates", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--default-template", default=DEFAULT_TEMPLATE)
    parser.add_argument("--no-template-search", action="store_true", help="skip step 0 and keep --default-template")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    settings = Settings.from_env()
    lumen, musk = LumenClient(settings), make_musk_backend(settings)
    tuning_manifest = json.loads(args.tuning_manifest.read_text(encoding="utf-8"))
    cases, families = load_manifest(json.loads(args.benchmark_manifest.read_text(encoding="utf-8")))
    labels = list(families[FAMILY])

    def load_set(name: str) -> list[tuple[str, str]]:
        items = []
        for row in tuning_manifest["sets"][name]:
            raw = (args.image_dir / row["image"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != row["sha256"]:
                raise SystemExit(f"Checksum mismatch for {row['image']}; rebuild with build_lc25000_tuning_sets.py.")
            items.append((data_url(raw), row["label"]))
        return items

    tuning_set, confirmation_set = load_set("tuning"), load_set("confirmation")
    test_set = []
    for label in labels:
        for case in [c for c in cases if c.ground_truth == label][: args.test_per_label]:
            raw = (ROOT / case.image_path).read_bytes()
            verify_image_checksum(raw, case.sha256, case.case_id)
            test_set.append((data_url(raw), label))

    def predict(prompts: dict[str, str], items: list[tuple[str, str]]) -> list[str]:
        predictions: list[str] = []
        for start in range(0, len(items), args.batch_size):
            batch = [image for image, _ in items[start : start + args.batch_size]]
            predictions += [p.label for p in musk.classify_batch(batch, prompts)]
        return predictions

    def correctness(items: list[tuple[str, str]]):
        return lambda prompts: [p == t for p, (_, t) in zip(predict(prompts, items), items)]

    def tuning_confusions(prompts: dict[str, str]) -> Counter:
        return Counter((t, p) for p, (_, t) in zip(predict(prompts, tuning_set), tuning_set) if p != t)

    def propose(focus: str | None, confusion: str) -> dict[str, list[str]]:
        raw, _ = lumen.complete(CANDIDATE_SYSTEM, candidate_request(labels, args.candidates, focus, confusion))
        return parse_candidates(raw, [focus] if focus else labels, args.candidates)

    started = time.time()
    log: list[dict] = []
    base = args.default_template if args.no_template_search else select_base(
        labels, correctness(tuning_set), correctness(confirmation_set), TEMPLATES, args.default_template, log)
    print(f"base template: {base}", flush=True)

    def base_confusions(prompts: dict[str, str]) -> Counter:
        return tuning_confusions(prompts)

    chosen = tune(labels, correctness(tuning_set), correctness(confirmation_set), propose, base_confusions, log, base)

    evaluate_test = correctness(test_set)
    prompt_sets = {
        "original MUSK (generic)": {label: _generic_prompt(label) for label in labels},
        "histology showing {label}": template_prompts(labels),
        "chosen base template": template_prompts(labels, base=base),
        "tuned": template_prompts(labels, chosen, base),
    }
    results = {name: evaluate_test(prompts) for name, prompts in prompt_sets.items()}
    test = {}
    for name, result in results.items():
        vs_original = compare(result, results["original MUSK (generic)"])
        vs_template = compare(result, results["histology showing {label}"])
        test[name] = {"correct": sum(result), "n": len(result), "prompts": prompt_sets[name],
                      "vs_original": vs_original.__dict__, "vs_template": vs_template.__dict__}
        print(f"test {name}: {sum(result)}/{len(result)} (vs template: +{vs_template.fixed} fixed, "
              f"-{vs_template.broken} broken, p={vs_template.p:.3g})", flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "lumen_model": settings.lumen_model or os.getenv("LUMEN_MODEL", ""), "base_template": base,
        "chosen_phrases": chosen,
        "sets": {"tuning": len(tuning_set), "confirmation": len(confirmation_set), "test": len(test_set)},
        "test": test, "minutes": round((time.time() - started) / 60, 1), "log": log,
    }, indent=1) + "\n", encoding="utf-8")
    print(f"Saved {args.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
