"""General (task-agnostic) template selection for MUSK across four tasks, with leave-one-task-out transfer tests.

    uv run python benchmarks/multitask-general-template/run_general.py      (MUSK reachable, e.g. through the tunnel)

Accept rule for a template T against the baseline B over a set of tasks (same spirit as the per-task bars):
  accuracy bar      mean per-task gain on tuning >= +1.0 point
  significance bar  paired sign test pooled over all tuning images, one-sided p < 0.05
  no-harm bar       no single task worse than -1.0 point on tuning
  confirmation      mean gain >= +0.5 point and no task worse than -1.0 point on the confirmation sets
B = MUSK's original prompt, `a histopathology image showing {label}`.

Leave-one-task-out (LOTO): for each task H, select using the other three tasks only, then score H's TEST set with
the baseline, the transferred template, and H's own per-task choice (selected on H's tuning set with the per-task
bars) for comparison. Finally, a general template selected on all four tasks.
Speed: two-stage screening (all templates on a 25% sample of each tuning set, top 8 in full), batches of 64,
3 requests in parallel. All comparisons inside this experiment use the same settings.
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
IMG_ROOT = REPO / ".benchmark-cache" / "multitask"
sys.path.insert(0, str(REPO))
from backends import MODELS, make_backend, output_name  # noqa: E402
from histoprompt.prompt_tuning import TEMPLATES, compare, passes_confirmation, passes_tuning_bars, sign_test_p, template_prompts  # noqa: E402

BASE = "a histopathology image showing {label}"
BATCH, WORKERS, SCREEN_FRAC, FINALISTS = 64, 3, 0.25, 8
parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
parser.add_argument("--model", choices=list(MODELS), default="musk", help="classifier to tune for (default musk)")
parser.add_argument("--skip-loto", action="store_true", help="only select the general template on all tasks")
args = parser.parse_args()
clf = make_backend(args.model)
man = json.loads((HERE / "manifest.json").read_text())
tasks = list(man["tasks"])
data = {t: {s: [("data:image/" + ("png" if r["image"].endswith(".png") else "jpeg") + ";base64,"
                 + base64.b64encode((IMG_ROOT / r["image"]).read_bytes()).decode(), r["label"])
                for r in man["tasks"][t]["sets"][s]] for s in ("tuning", "confirmation", "test")} for t in tasks}
labels = {t: man["tasks"][t]["labels"] for t in tasks}
cache: dict = {}


def run(task: str, split: str, template: str, items=None) -> list[bool]:
    key = (task, split, template, None if items is None else len(items))
    if key in cache:
        return cache[key]
    items = items if items is not None else data[task][split]
    prompts = template_prompts(labels[task], base=template)
    chunks = [items[i:i + BATCH] for i in range(0, len(items), BATCH)]
    with ThreadPoolExecutor(WORKERS) as ex:
        preds = list(ex.map(lambda ch: [p.label for p in clf.classify_batch([x for x, _ in ch], prompts)], chunks))
    ok = [p == t for ps, ch in zip(preds, chunks) for p, (_, t) in zip(ps, ch)]
    cache[key] = ok
    return ok


def screen_items(task):
    items = data[task]["tuning"]
    step = int(1 / SCREEN_FRAC)
    return items[::step]


def multi(templates, task_set, split):
    return {t: {k: run(k, split, t) for k in task_set} for t in templates}


def accept_general(task_set, log):
    """Select a template for task_set; return (template, details)."""
    # stage 1: screen all templates on a 25% sample of each tuning set
    screen = {t: sum(sum(run(k, "tuning", t, screen_items(k))) / len(screen_items(k)) for k in task_set) / len(task_set)
              for t in dict.fromkeys([BASE, *TEMPLATES])}
    finalists = sorted(screen, key=screen.get, reverse=True)[:FINALISTS]
    if BASE not in finalists:
        finalists.append(BASE)
    # stage 2: full tuning sets for finalists
    full = multi(finalists, task_set, "tuning")
    def gains(res, t):
        return {k: (sum(res[t][k]) - sum(res[BASE][k])) / len(res[t][k]) for k in task_set}
    ranked = sorted(finalists, key=lambda t: sum(gains(full, t).values()), reverse=True)
    for t in ranked:
        if t == BASE:
            break
        g = gains(full, t)
        pooled_new = [x for k in task_set for x in full[t][k]]
        pooled_old = [x for k in task_set for x in full[BASE][k]]
        comp = compare(pooled_new, pooled_old)
        mean_gain = sum(g.values()) / len(g)
        ok_tune = mean_gain >= 0.01 and comp.p < 0.05 and min(g.values()) >= -0.01
        entry = {"template": t, "tuning_gain_per_task": g, "tuning_mean_gain": mean_gain, "fixed": comp.fixed,
                 "broken": comp.broken, "p": comp.p, "passes_tuning": ok_tune}
        if ok_tune:
            conf = {k: (sum(run(k, "confirmation", t)) - sum(run(k, "confirmation", BASE))) / len(data[k]["confirmation"])
                    for k in task_set}
            ok_conf = sum(conf.values()) / len(conf) >= 0.005 and min(conf.values()) >= -0.01
            entry.update({"confirmation_gain_per_task": conf, "passes_confirmation": ok_conf})
            log.append(entry)
            if ok_conf:
                return t, entry
        else:
            log.append(entry)
    return BASE, {"template": BASE, "note": "no template cleared the bars"}


def accept_single(task, log):
    """Per-task choice (the tailored comparison), with the per-task bars."""
    screen = {t: sum(run(task, "tuning", t, screen_items(task))) for t in dict.fromkeys([BASE, *TEMPLATES])}
    finalists = sorted(screen, key=screen.get, reverse=True)[:FINALISTS]
    if BASE not in finalists:
        finalists.append(BASE)
    res = {t: run(task, "tuning", t) for t in finalists}
    for t in sorted(finalists, key=lambda t: sum(res[t]), reverse=True):
        if t == BASE:
            break
        comp = compare(res[t], res[BASE])
        if passes_tuning_bars(comp):
            conf = compare(run(task, "confirmation", t), run(task, "confirmation", BASE))
            log.append({"task": task, "template": t, "tuning_gain": comp.gain, "p": comp.p, "confirmation_gain": conf.gain,
                        "accepted": passes_confirmation(conf)})
            if passes_confirmation(conf):
                return t
    return BASE


def test_row(task, template):
    ok = run(task, "test", template)
    base = run(task, "test", BASE)
    c = compare(ok, base)
    return {"template": template, "correct": sum(ok), "n": len(ok), "accuracy": sum(ok) / len(ok),
            "vs_baseline": {"gain": c.gain, "fixed": c.fixed, "broken": c.broken,
                            "p": sign_test_p(max(c.fixed, c.broken), min(c.fixed, c.broken))}}


t0 = time.time()
out = {"model": args.model, "baseline": BASE, "tasks": {t: {s: len(v) for s, v in data[t].items()} for t in tasks}, "loto": {}, "settings":
       {"batch": BATCH, "workers": WORKERS, "screen_fraction": SCREEN_FRAC, "finalists": FINALISTS}}
for held in ([] if args.skip_loto else tasks):
    others = [t for t in tasks if t != held]
    log: list = []
    general, info = accept_general(others, log)
    own_log: list = []
    own = accept_single(held, own_log)
    out["loto"][held] = {"selected_on": others, "transferred_template": general, "selection": info, "log": log,
                         "own_template": own, "own_log": own_log,
                         "test": {"baseline": test_row(held, BASE), "transferred": test_row(held, general),
                                  "own (tailored)": test_row(held, own)}}
    r = out["loto"][held]["test"]
    print(f"[{held}] transferred '{general}': {r['transferred']['correct']}/{r['transferred']['n']} vs baseline "
          f"{r['baseline']['correct']}  |  own '{own}': {r['own (tailored)']['correct']}  ({(time.time()-t0)/60:.1f} min)",
          flush=True)
log = []
g_all, info = accept_general(tasks, log)
out["general_all_tasks"] = {"template": g_all, "selection": info, "log": log,
                            "test": {t: {"baseline": test_row(t, BASE), "general": test_row(t, g_all)} for t in tasks}}
print(f"[all tasks] general template: '{g_all}'", flush=True)
for t in tasks:
    r = out["general_all_tasks"]["test"][t]
    print(f"   {t}: {r['general']['correct']}/{r['general']['n']} vs baseline {r['baseline']['correct']}", flush=True)
out["minutes"] = round((time.time() - t0) / 60, 1)
(HERE / output_name("results", args.model)).write_text(json.dumps(out, indent=1, default=str))
print("saved", output_name("results", args.model), flush=True)
