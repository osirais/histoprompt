from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .lumen import LumenClient
from .pipeline import PROMPT_BUILDER_SYSTEM, _extract_prompts, _generic_prompt, _json_from_model
from .rag import EvidenceIndex


STRATEGIES = ("label_only", "generic", "curated", "evidence_generated")


def verify_image_checksum(raw: bytes, expected: str, case_id: str) -> None:
    if not expected:
        return
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise ValueError(
            f"Image checksum mismatch for {case_id}: expected {expected}, got {actual}."
        )


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    family: str
    ground_truth: str
    source_url: str
    source_note: str
    image_path: str = ""
    image_url: str = ""
    sha256: str = ""
    source_license: str = ""


def load_manifest(value: dict[str, Any]) -> tuple[list[BenchmarkCase], dict[str, dict[str, str]]]:
    families = value.get("families")
    cases = value.get("cases", [])
    case_sets = value.get("case_sets", [])
    if not isinstance(families, dict) or not isinstance(cases, list) or not isinstance(case_sets, list):
        raise ValueError("Benchmark manifest requires families and cases or case_sets.")

    normalized_families: dict[str, dict[str, str]] = {}
    for family, item in families.items():
        if not isinstance(item, dict) or not isinstance(item.get("prompts"), dict):
            raise ValueError(f"Benchmark family {family!r} requires a prompts mapping.")
        prompts = {
            str(label).strip(): str(prompt).strip()
            for label, prompt in item["prompts"].items()
            if str(label).strip() and str(prompt).strip()
        }
        if len(prompts) < 2:
            raise ValueError(f"Benchmark family {family!r} requires at least two labels.")
        normalized_families[str(family)] = prompts

    expanded_cases = list(cases)
    for case_set in case_sets:
        if not isinstance(case_set, dict) or not isinstance(case_set.get("images"), list):
            raise ValueError("Every benchmark case set requires an images list.")
        prefix = str(case_set.get("id_prefix", "")).strip()
        for index, image in enumerate(case_set["images"], 1):
            if not isinstance(image, dict):
                raise ValueError(f"Every image in case set {prefix!r} must be an object.")
            expanded_cases.append(
                {
                    **case_set,
                    **image,
                    "id": str(image.get("id") or f"{prefix}-{index:02d}"),
                }
            )

    normalized_cases: list[BenchmarkCase] = []
    seen: set[str] = set()
    for item in expanded_cases:
        if not isinstance(item, dict):
            raise ValueError("Every benchmark case must be an object.")
        case = BenchmarkCase(
            case_id=str(item.get("id", "")).strip(),
            family=str(item.get("family", "")).strip(),
            ground_truth=str(item.get("ground_truth", "")).strip(),
            source_url=str(item.get("source_url", "")).strip(),
            source_note=str(item.get("source_note", "")).strip(),
            image_path=str(item.get("image_path", "")).strip(),
            image_url=str(item.get("image_url", "")).strip(),
            sha256=str(item.get("sha256", "")).strip().lower(),
            source_license=str(item.get("source_license", "")).strip(),
        )
        if not all((case.case_id, case.family, case.ground_truth, case.source_url)):
            raise ValueError("Every benchmark case requires id, family, ground_truth, and source_url.")
        if not case.image_path and not case.image_url:
            raise ValueError(f"Benchmark case {case.case_id!r} requires image_path or image_url.")
        if case.case_id in seen:
            raise ValueError(f"Duplicate benchmark case id: {case.case_id}")
        if case.family not in normalized_families:
            raise ValueError(f"Unknown family {case.family!r} in case {case.case_id!r}.")
        if case.ground_truth not in normalized_families[case.family]:
            raise ValueError(f"Ground truth for {case.case_id!r} is not a family label.")
        seen.add(case.case_id)
        normalized_cases.append(case)
    if not normalized_cases:
        raise ValueError("Benchmark manifest has no cases.")
    return normalized_cases, normalized_families


def prompts_for_strategy(
    strategy: str,
    curated_prompts: dict[str, str],
    generated_prompts: dict[str, str] | None = None,
) -> dict[str, str]:
    labels = list(curated_prompts)
    if strategy == "label_only":
        return {label: label for label in labels}
    if strategy == "generic":
        return {label: _generic_prompt(label) for label in labels}
    if strategy == "curated":
        return dict(curated_prompts)
    if strategy == "evidence_generated":
        if generated_prompts is None:
            raise ValueError("Evidence-generated prompts have not been created.")
        return {label: generated_prompts.get(label, _generic_prompt(label)) for label in labels}
    raise ValueError(f"Unknown benchmark strategy: {strategy}")


def generate_evidence_prompts(
    family: str,
    curated_prompts: dict[str, str],
    evidence_index: EvidenceIndex,
    lumen: LumenClient,
    requested_model: str = "",
) -> tuple[dict[str, str], str, list[dict[str, str | float]]]:
    labels = list(curated_prompts)
    evidence = evidence_index.search(" ".join([family, *labels]), 6)
    evidence_text = "\n\n".join(
        f"[{item.source_id}] {item.title} ({item.year or 'year unknown'})\n{item.text}"
        for item in evidence
    )
    request = f"""Create visually discriminative microscopic features for every candidate label in this {family} zero-shot benchmark.

CANDIDATE LABELS
{json.dumps(labels, indent=2)}

RETRIEVED LOCAL EVIDENCE
{evidence_text or 'No matching evidence was retrieved. Use established microscopic features and remain conservative.'}

This is a label-level benchmark prompt, not a patient case. Do not infer or mention a ground-truth label, patient, report, or image. Keep each feature phrase under 25 words, do not repeat the diagnosis label inside it, and retain every candidate label exactly as written. Return exactly:
{{
  "features": {{
    "exact candidate label": "short microscopic feature phrase"
  }}
}}"""
    raw, model = lumen.complete(PROMPT_BUILDER_SYSTEM, request, requested_model)
    return _extract_prompts(_json_from_model(raw), labels), model, [item.as_dict() for item in evidence]


def summarize_results(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    summary: dict[str, dict[str, float | int]] = {}
    for strategy in STRATEGIES:
        selected = [row for row in rows if row.get("strategy") == strategy]
        successful = [row for row in selected if not row.get("error")]
        correct = sum(bool(row.get("correct")) for row in successful)
        mean_score = (
            sum(float(row.get("score", 0.0)) for row in successful) / len(successful)
            if successful
            else 0.0
        )
        summary[strategy] = {
            "attempted": len(selected),
            "successful": len(successful),
            "correct": correct,
            "accuracy": round(correct / len(successful), 4) if successful else 0.0,
            "mean_top_score": round(mean_score, 6),
        }
    return summary
