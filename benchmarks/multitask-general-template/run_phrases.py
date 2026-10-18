"""Two-tier prompts for MUSK: the shared template from run_general.py plus label phrases tuned per task.

For every task, step 1 of the validated tuning (histoprompt.prompt_tuning.tune: LLM phrases, accuracy and
significance bars on the tuning set, confirmation set) runs on top of the general template selected on all four
tasks (results.json -> general_all_tasks). Step 0 is not repeated. The test sets are scored once at the end.

    LUMEN_MODEL=gemma-4-31b-it LUMEN_MAX_TOKENS=16000 uv run python benchmarks/multitask-general-template/run_phrases.py

Speed: batches of 64, 3 requests in parallel per task, all four tasks in parallel, and repeated prompt sets are
scored once. Batch size matches run_general.py, so the numbers compare directly with results.json.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
IMG_ROOT = REPO / ".benchmark-cache" / "multitask"
sys.path.insert(0, str(REPO))
from histoprompt.config import Settings  # noqa: E402
from histoprompt.lumen import LumenClient  # noqa: E402
from backends import MODELS, make_backend, output_name  # noqa: E402
from histoprompt.prompt_tuning import (  # noqa: E402
    CANDIDATE_SYSTEM, candidate_request, compare, parse_candidates, sign_test_p, template_prompts, tune,
)

BASE = "a histopathology image showing {label}"
BATCH, WORKERS, CANDIDATES = 64, 3, 8
settings = Settings.from_env()
parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
parser.add_argument("--model", choices=list(MODELS), default="musk", help="classifier to tune for (default musk)")
parser.add_argument("--template", help="start from this template instead of the general one, e.g. the baseline")
parser.add_argument("--tasks", nargs="+", help="only these tasks (default: all)")
parser.add_argument("--reuse-candidates", type=Path,
                    help="results_phrases file whose first-round LLM candidates are reused, so only the template differs")
parser.add_argument("--output", help="output file name (default results_phrases[_<model>].json)")
args = parser.parse_args()
clf, lumen = make_backend(args.model), LumenClient(settings)
man = json.loads((HERE / "manifest.json").read_text())
general = args.template or json.loads((HERE / output_name("results", args.model)).read_text())["general_all_tasks"]["template"]
tasks = args.tasks or list(man["tasks"])
reused = json.loads(args.reuse_candidates.read_text())["tasks"] if args.reuse_candidates else {}
data = {t: {s: [("data:image/" + ("png" if r["image"].endswith(".png") else "jpeg") + ";base64,"
                 + base64.b64encode((IMG_ROOT / r["image"]).read_bytes()).decode(), r["label"])
                for r in man["tasks"][t]["sets"][s]] for s in ("tuning", "confirmation", "test")} for t in tasks}
labels = {t: man["tasks"][t]["labels"] for t in tasks}
cache: dict = {}


def predict(task: str, split: str, prompts: dict[str, str]) -> list[str]:
    key = (task, split, tuple(sorted(prompts.items())))
    if key not in cache:
        items = data[task][split]
        chunks = [items[i:i + BATCH] for i in range(0, len(items), BATCH)]
        with ThreadPoolExecutor(WORKERS) as ex:
            preds = list(ex.map(lambda ch: [p.label for p in clf.classify_batch([x for x, _ in ch], prompts)], chunks))
        cache[key] = [p for ps in preds for p in ps]
    return cache[key]


def correctness(task: str, split: str):
    return lambda prompts: [p == t for p, (_, t) in zip(predict(task, split, prompts), data[task][split])]


def run_task(task: str) -> dict:
    t0 = time.time()
    labs = labels[task]

    def propose(focus, confusion):
        if focus is None and task in reused:
            return next(e["candidates"] for e in reused[task]["log"] if e.get("step") == "candidates")
        raw, _ = lumen.complete(CANDIDATE_SYSTEM.replace("MUSK", MODELS[args.model]),
                                candidate_request(labs, CANDIDATES, focus, confusion).replace("MUSK", MODELS[args.model]))
        return parse_candidates(raw, [focus] if focus else labs, CANDIDATES)

    def confusions(prompts):
        items = data[task]["tuning"]
        return Counter((t, p) for p, (_, t) in zip(predict(task, "tuning", prompts), items) if p != t)

    log: list = []
    chosen = tune(labs, correctness(task, "tuning"), correctness(task, "confirmation"), propose, confusions, log, general)
    sets = {"baseline": template_prompts(labs, base=BASE), "general template": template_prompts(labs, base=general),
            "general template + phrases": template_prompts(labs, chosen, general)}
    res = {name: correctness(task, "test")(p) for name, p in sets.items()}
    test = {}
    for name, ok in res.items():
        vb, vg = compare(ok, res["baseline"]), compare(ok, res["general template"])
        test[name] = {"correct": sum(ok), "n": len(ok), "prompts": sets[name],
                      "vs_baseline": {"fixed": vb.fixed, "broken": vb.broken,
                                      "p": sign_test_p(max(vb.fixed, vb.broken), min(vb.fixed, vb.broken))},
                      "vs_general_template": {"fixed": vg.fixed, "broken": vg.broken,
                                              "p": sign_test_p(max(vg.fixed, vg.broken), min(vg.fixed, vg.broken))}}
    r = test
    print(f"[{task}] baseline {r['baseline']['correct']}, general {r['general template']['correct']}, "
          f"+phrases {r['general template + phrases']['correct']} /{r['baseline']['n']}  phrases: "
          f"{ {k: v for k, v in chosen.items() if v} }  ({(time.time() - t0) / 60:.1f} min)", flush=True)
    return {"chosen_phrases": chosen, "test": test, "log": log, "minutes": round((time.time() - t0) / 60, 1)}


t0 = time.time()
with ThreadPoolExecutor(len(tasks)) as ex:
    per_task = dict(zip(tasks, ex.map(run_task, tasks)))
out = {"model": args.model, "lumen_model": settings.lumen_model or os.getenv("LUMEN_MODEL", ""), "baseline": BASE,
       "general_template": general, "settings": {"batch": BATCH, "workers": WORKERS, "candidates": CANDIDATES},
       "reused_candidates_from": str(args.reuse_candidates or ""), "tasks": per_task, "minutes": round((time.time() - t0) / 60, 1)}
(HERE / (args.output or output_name("results_phrases", args.model))).write_text(json.dumps(out, indent=1, default=str))
print("saved", args.output or output_name("results_phrases", args.model), flush=True)
