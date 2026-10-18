"""Validated label-prompt tuning for MUSK.

Searches short phrases to add to MUSK's template, `histology showing {label} with {phrase}`, using labelled images.
A phrase is accepted for a label only if it clears all three bars:

  accuracy bar      at least ACCURACY_BAR (1.0 percentage point) more correct on the tuning set
  significance bar  paired exact sign test on the tuning set (images fixed vs images broken), one-sided p < P_BAR
  confirmation      at least CONFIRM_BAR (0.5 points) more correct on a separate confirmation set

Accuracy (right or wrong) is the only measure. Labels with no accepted phrase keep the plain template.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from .pipeline import _json_from_model

ACCURACY_BAR = 0.010
CONFIRM_BAR = 0.005
P_BAR = 0.05

STOP_WORDS = set(
    "a an and the of with in on by or to for from as at no without within into along its their is are "
    "showing histology tissue cells cell features feature pattern patterns".split()
)
CANDIDATE_SYSTEM = (
    "You write short captions for the selected CLIP-style pathology vision-language model that must tell apart a "
    "fixed set of diagnoses on H&E images. It responds best to short, plain caption phrases. "
    "Return only valid JSON."
)


def template_prompts(labels: Sequence[str], phrases: dict[str, str] | None = None) -> dict[str, str]:
    """MUSK prompts: `histology showing {label}`, plus ` with {phrase}` where a phrase is set."""
    phrases = phrases or {}
    return {
        label: f"histology showing {label} with {phrases[label]}" if phrases.get(label) else f"histology showing {label}"
        for label in labels
    }


def sign_test_p(fixed: int, broken: int) -> float:
    """One-sided exact sign test: probability of at least `fixed` wins among the changed images by chance."""
    changed = fixed + broken
    if changed == 0:
        return 1.0
    return sum(math.comb(changed, i) for i in range(fixed, changed + 1)) / 2**changed


@dataclass(frozen=True)
class Comparison:
    gain: float          # accuracy difference, candidate minus current
    fixed: int           # images the candidate gets right that the current prompts got wrong
    broken: int          # images the candidate gets wrong that the current prompts got right
    p: float             # sign_test_p(fixed, broken)


def compare(candidate: Sequence[bool], current: Sequence[bool]) -> Comparison:
    if len(candidate) != len(current) or not candidate:
        raise ValueError("Comparisons need two non-empty result lists of the same length.")
    fixed = sum(c and not o for c, o in zip(candidate, current))
    broken = sum(o and not c for c, o in zip(candidate, current))
    return Comparison((sum(candidate) - sum(current)) / len(candidate), fixed, broken, sign_test_p(fixed, broken))


def passes_tuning_bars(result: Comparison, accuracy_bar: float = ACCURACY_BAR, p_bar: float = P_BAR) -> bool:
    return result.gain >= accuracy_bar and result.p < p_bar


def passes_confirmation(result: Comparison, confirm_bar: float = CONFIRM_BAR) -> bool:
    return result.gain >= confirm_bar


def _content_words(text: str, labels: Sequence[str]) -> set[str]:
    label_words = {word for label in labels for word in re.findall(r"[a-z]+", label.lower())}
    return {
        word
        for word in re.findall(r"[a-z]+", text.lower())
        if word not in STOP_WORDS and word not in label_words and len(word) > 2
    }


def overlap_filter(candidates: dict[str, list[str]], labels: Sequence[str]) -> tuple[dict[str, list[str]], list[str]]:
    """Drop phrases that share a content word with another label's phrases (one shared phrase can make MUSK send
    every image of one label to another)."""
    words = {
        label: set().union(*[_content_words(p, labels) for p in phrases]) if phrases else set()
        for label, phrases in candidates.items()
    }
    kept: dict[str, list[str]] = {}
    dropped: list[str] = []
    for label, phrases in candidates.items():
        others = set().union(*[w for other, w in words.items() if other != label]) if len(words) > 1 else set()
        kept[label] = []
        for phrase in phrases:
            clash = _content_words(phrase, labels) & others
            if clash:
                dropped.append(f"{label}: '{phrase}' shares {sorted(clash)}")
            else:
                kept[label].append(phrase)
    return kept, dropped


def candidate_request(labels: Sequence[str], k: int, focus: str | None = None, confusion: str = "") -> str:
    targets = [focus] if focus else list(labels)
    extra = (
        f"\nOn tuning images, MUSK still makes these mistakes: {confusion}. Write phrases for '{focus}' that point "
        "to morphology that is clearly ABSENT in the label(s) it is confused with."
        if focus
        else ""
    )
    return f"""Candidate diagnoses (MUSK must choose one per image): {json.dumps(list(labels))}.
For each of these labels: {json.dumps(targets)}, write {k} different candidate caption phrases.
Each phrase: 2 to 6 words, one H&E-visible architectural or cytological feature that is characteristic of that label and absent in the other candidates. No feature common to all carcinomas (pleomorphism, atypia, hyperchromasia, nucleoli, mitoses, necrosis, desmoplasia). No immunostains, markers, or clinical facts. Do not use the diagnosis name. Lowercase, no punctuation.{extra}
Return exactly: {{"candidates": {{"<label>": ["phrase", ...]}}}}"""


def parse_candidates(raw: str, targets: Sequence[str], k: int) -> dict[str, list[str]]:
    parsed = _json_from_model(raw) or {}
    candidates = parsed.get("candidates", {}) if isinstance(parsed, dict) else {}
    if not isinstance(candidates, dict):
        candidates = {}
    out: dict[str, list[str]] = {}
    for label in targets:
        found = next((v for key, v in candidates.items() if str(key).strip().lower() == label.lower()), [])
        if not isinstance(found, list):
            found = []
        cleaned = [re.sub(r"[^a-z0-9 \-]", "", str(p).lower()).strip() for p in found]
        out[label] = [p for p in cleaned if p][:k]
    return out


Evaluate = Callable[[dict[str, str]], list[bool]]


def tune(
    labels: Sequence[str],
    evaluate_tuning: Evaluate,
    evaluate_confirmation: Evaluate,
    propose: Callable[[str | None, str], dict[str, list[str]]],
    confusions: Callable[[dict[str, str]], Counter],
    log: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """Return the accepted phrase per label ('' = plain template).

    evaluate_*: prompts -> per-image correctness on that set. propose(focus, confusion): LLM candidates (all labels
    when focus is None). confusions(prompts): Counter of (true, predicted) errors on the tuning set."""
    log = log if log is not None else []
    chosen = {label: "" for label in labels}
    current = evaluate_tuning(template_prompts(labels, chosen))
    log.append({"step": "baseline", "tuning_accuracy": sum(current) / len(current)})

    def try_label(label: str, phrases: list[str], step: str) -> None:
        nonlocal current
        best = None
        for phrase in phrases:
            result = evaluate_tuning(template_prompts(labels, {**chosen, label: phrase}))
            comp = compare(result, current)
            log.append({"step": step, "label": label, "phrase": phrase, **comp.__dict__})
            if passes_tuning_bars(comp) and (best is None or comp.gain > best[1].gain):
                best = (phrase, comp, result)
        if best is None:
            log.append({"step": step, "label": label, "accepted": None})
            return
        phrase, comp, result = best
        confirm = compare(
            evaluate_confirmation(template_prompts(labels, {**chosen, label: phrase})),
            evaluate_confirmation(template_prompts(labels, chosen)),
        )
        accepted = passes_confirmation(confirm)
        log.append({"step": f"{step} confirmation", "label": label, "phrase": phrase,
                    "tuning_gain": comp.gain, "tuning_p": comp.p, "confirmation_gain": confirm.gain,
                    "accepted": accepted})
        if accepted:
            chosen[label] = phrase
            current = result

    candidates, dropped = overlap_filter(propose(None, ""), labels)
    log.append({"step": "candidates", "candidates": candidates, "dropped": dropped})
    for label in labels:
        try_label(label, candidates.get(label, []), "round 1")

    remaining = confusions(template_prompts(labels, chosen))
    if remaining:
        (focus, _), _ = remaining.most_common(1)[0]
        confusion = "; ".join(f"{t} called {p} ({n}x)" for (t, p), n in remaining.most_common(3))
        fresh = propose(focus, confusion)
        merged = {**{label: [chosen[label]] if chosen[label] else [] for label in labels}, **fresh}
        filtered, _ = overlap_filter(merged, labels)
        phrases = [p for p in filtered.get(focus, []) if p != chosen[focus]]
        log.append({"step": "feedback candidates", "label": focus, "confusion": confusion, "candidates": phrases})
        try_label(focus, phrases, "feedback")
    return chosen
