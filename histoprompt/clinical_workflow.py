"""Shared construction and parsing for the clinician-style case workflow."""
from __future__ import annotations

import json
import re
from typing import Any, Sequence


PROMPT_BUILDER_SYSTEM = """You extract concise visual features for zero-shot histopathology prompts.
For each candidate label, return only two to four distinctive microscopic features as a short noun phrase. Include only features visible in a pathology image, do not repeat the label, do not add generic boilerplate, and do not invent patient facts. Return only the requested valid JSON."""


REVIEW_SYSTEM_PROMPT = """You are the evidence-review layer in a research-only computational pathology prototype.
Your task is to critically evaluate pathology vision-model classifications against the supplied report and retrieved literature excerpts. Do not invent patient facts, citations, or evidence. Do not claim a diagnosis. Clearly separate model output from evidence and uncertainty. Return only valid JSON matching the requested schema."""


def json_from_model(text: str) -> dict[str, Any] | None:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate)
    try:
        value = json.loads(candidate)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", candidate, re.DOTALL)
        if not match:
            return None
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            return None


def generic_prompt(label: str) -> str:
    return f"a histopathology image showing {label}"


def histology_prompt(label: str) -> str:
    return f"histology showing {label}"


def extract_prompts(
    value: dict[str, Any] | None, labels: Sequence[str]
) -> dict[str, str]:
    raw_features = value.get("features", {}) if isinstance(value, dict) else {}
    if not isinstance(raw_features, dict):
        raw_features = {}
    raw_prompts = value.get("prompts", {}) if isinstance(value, dict) else {}
    if not isinstance(raw_prompts, dict):
        raw_prompts = {}
    normalized = {
        str(key).strip().casefold(): str(description).strip()
        for key, description in raw_prompts.items()
        if str(description).strip()
    }
    normalized_features = {
        str(key).strip().casefold(): " ".join(str(features).strip().split()[:28])
        for key, features in raw_features.items()
        if str(features).strip()
    }
    return {
        label: (
            f"{label} with {normalized_features[label.casefold()]}"
            if label.casefold() in normalized_features
            else normalized.get(label.casefold(), generic_prompt(label))
        )[:800]
        for label in labels
    }


def format_evidence(evidence: Sequence[Any]) -> str:
    return "\n\n".join(
        f"[{item.source_id}] {item.title} ({item.year or 'year unknown'})\n{item.text}"
        for item in evidence
    )


def build_prompt_generation_request(
    report: str, labels: Sequence[str], evidence_text: str
) -> str:
    return f"""Extract two to four visually discriminative microscopic features for every candidate label.

DE-IDENTIFIED REPORT
{report}

CANDIDATE LABELS
{json.dumps(list(labels), indent=2)}

RETRIEVED LOCAL EVIDENCE
{evidence_text or 'No matching evidence was retrieved. Use established microscopic features and remain conservative.'}

Keep each feature phrase under 25 words, do not repeat the diagnosis label inside it, and retain every candidate label exactly as written. Return exactly:
{{
  "features": {{
    "exact candidate label": "short microscopic feature phrase"
  }}
}}"""


def parse_lumen_prompts(
    raw: str, labels: Sequence[str]
) -> tuple[dict[str, str], dict[str, Any] | None]:
    parsed = json_from_model(raw)
    return extract_prompts(parsed, labels), parsed


def _top_result_text(result: dict[str, Any] | None) -> str:
    if not isinstance(result, dict):
        return "unavailable"
    label = str(result.get("label", "unavailable"))
    try:
        score = f"{float(result.get('probability')):.6f}"
    except (TypeError, ValueError):
        score = "unavailable"
    return f"{label} (returned score {score})"


def build_review_request(
    *,
    report: str,
    labels: Sequence[str],
    prompts: dict[str, str],
    model_results: dict[str, dict[str, dict[str, Any] | None]],
    evidence_text: str,
) -> str:
    sections = []
    for model, results in model_results.items():
        sections.append(
            "\n".join(
                [
                    model.upper(),
                    "IMAGE-ONLY BASELINE: "
                    + _top_result_text(results.get("baseline")),
                    "CASE-SPECIFIC LUMEN PROMPT: "
                    + _top_result_text(results.get("enhanced")),
                ]
            )
        )
    return f"""Review this research case.

DE-IDENTIFIED REPORT
{report}

CANDIDATE LABELS
{json.dumps(list(labels), indent=2)}

CASE-SPECIFIC PROMPTS
{json.dumps(prompts, indent=2)}

VISION-MODEL OUTPUTS
{chr(10).join(sections)}

RETRIEVED LOCAL EVIDENCE
{evidence_text or 'No matching evidence was retrieved.'}

Return exactly this JSON object:
{{
  "assessment": "one concise research assessment",
  "classification": "one exact candidate label or indeterminate",
  "confidence": 0.0,
  "rationale": ["2-4 short evidence-linked reasons using [source_id] notation"],
  "discrepancies": ["conflicts or missing facts"],
  "evidence_used": ["source_id"],
  "recommended_review": ["specific human review or additional test, not treatment advice"],
  "limitations": ["important limitations"]
}}
Confidence must be a number from 0 to 1 and must reflect both model uncertainty and evidence quality. The classification must be one exact candidate label or the word indeterminate."""


def normalize_review_classification(
    review: dict[str, Any] | None, labels: Sequence[str]
) -> str:
    if not isinstance(review, dict):
        return "indeterminate"
    candidate = str(review.get("classification", "")).strip().casefold()
    if candidate == "indeterminate":
        return "indeterminate"
    normalized = {label.casefold(): label for label in labels}
    return normalized.get(candidate, "indeterminate")


# Compatibility aliases for existing imports from histoprompt.pipeline.
_json_from_model = json_from_model
_generic_prompt = generic_prompt
_histology_prompt = histology_prompt
_extract_prompts = extract_prompts
