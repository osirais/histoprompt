from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .config import Settings
from .lumen import LumenClient
from .musk_backend import make_musk_backend
from .rag import EvidenceIndex


PROMPT_BUILDER_SYSTEM = """You extract concise visual features for zero-shot histopathology prompts.
For each candidate label, return only two to four distinctive microscopic features as a short noun phrase. Include only features visible in a pathology image, do not repeat the label, do not add generic boilerplate, and do not invent patient facts. Return only the requested valid JSON."""


REVIEW_SYSTEM_PROMPT = """You are the evidence-review layer in a research-only computational pathology prototype.
Your task is to critically evaluate a vision model's zero-shot classification against the supplied report and retrieved literature excerpts. Do not invent patient facts, citations, or evidence. Do not claim a diagnosis. Clearly separate the model output from evidence and uncertainty. Return only valid JSON matching the requested schema."""


def _json_from_model(text: str) -> dict[str, Any] | None:
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


def _generic_prompt(label: str) -> str:
    return f"a histopathology image showing {label}"


def _extract_prompts(value: dict[str, Any] | None, labels: list[str]) -> dict[str, str]:
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
            else normalized.get(label.casefold(), _generic_prompt(label))
        )[:800]
        for label in labels
    }


@dataclass
class AnalysisPipeline:
    settings: Settings
    evidence_index: EvidenceIndex
    lumen: LumenClient

    @classmethod
    def create(cls, settings: Settings) -> "AnalysisPipeline":
        return cls(settings, EvidenceIndex(settings.corpus_path), LumenClient(settings))

    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        image = str(payload.get("image", ""))
        report = str(payload.get("report", "")).strip()
        labels = [str(label).strip() for label in payload.get("labels", []) if str(label).strip()]
        if not image:
            raise ValueError("A pathology image is required.")
        if not report:
            raise ValueError("A de-identified report is required.")
        if len(labels) < 2:
            raise ValueError("Provide at least two candidate labels for zero-shot comparison.")
        if len(labels) > 30:
            raise ValueError("At most 30 candidate labels are supported in one run.")

        query = " ".join([report, *labels])
        evidence = self.evidence_index.search(query, int(payload.get("top_k", 5)))
        evidence_text = "\n\n".join(
            f"[{item.source_id}] {item.title} ({item.year or 'year unknown'})\n{item.text}"
            for item in evidence
        )
        prompt_generation_request = f"""Extract two to four visually discriminative microscopic features for every candidate label.

DE-IDENTIFIED REPORT
{report}

CANDIDATE LABELS
{json.dumps(labels, indent=2)}

RETRIEVED LOCAL EVIDENCE
{evidence_text or 'No matching evidence was retrieved. Use established microscopic features and remain conservative.'}

Keep each feature phrase under 25 words, do not repeat the diagnosis label inside it, and retain every candidate label exactly as written. Return exactly:
{{
  "features": {{
    "exact candidate label": "short microscopic feature phrase"
  }}
}}"""
        requested_model = str(payload.get("model", ""))
        raw_prompt_plan, prompt_model = self.lumen.complete(
            PROMPT_BUILDER_SYSTEM,
            prompt_generation_request,
            requested_model,
        )
        musk_prompts = _extract_prompts(_json_from_model(raw_prompt_plan), labels)
        generic_prompts = {label: _generic_prompt(label) for label in labels}
        musk = make_musk_backend(self.settings)
        baseline_predictions = musk.classify(image, generic_prompts)
        predictions = musk.classify(image, musk_prompts)
        baseline_text = "\n".join(
            f"- {item.label}: {item.probability:.4f}"
            for item in baseline_predictions
        )
        prediction_text = "\n".join(
            f"- {item.label}: {item.probability:.4f}" for item in predictions
        )
        review_prompt = f"""Review this case.

DE-IDENTIFIED REPORT
{report}

PLAIN MUSK BASELINE SCORES
{baseline_text}

CASE-SPECIFIC MUSK PROMPTS
{json.dumps(musk_prompts, indent=2)}

PROMPT-ENHANCED MUSK SCORES
{prediction_text}

RETRIEVED LOCAL EVIDENCE
{evidence_text or 'No matching evidence was retrieved.'}

Return exactly this JSON object:
{{
  "assessment": "one concise research assessment",
  "classification": "best-supported candidate label or indeterminate",
  "confidence": 0.0,
  "rationale": ["2-4 short evidence-linked reasons using [source_id] notation"],
  "discrepancies": ["conflicts or missing facts"],
  "evidence_used": ["source_id"],
  "recommended_review": ["specific human review or additional test, not treatment advice"],
  "limitations": ["important limitations"]
}}
Confidence must be a number from 0 to 1 and must reflect both model uncertainty and evidence quality."""
        raw, model = self.lumen.complete(
            REVIEW_SYSTEM_PROMPT,
            review_prompt,
            prompt_model,
        )
        structured = _json_from_model(raw)
        return {
            "musk_prompts": musk_prompts,
            "baseline_predictions": [
                item.as_dict() for item in baseline_predictions
            ],
            "musk_predictions": [item.as_dict() for item in predictions],
            # Keep the measured MUSK result as the primary classification until a
            # prompt variant has beaten it on a held-out benchmark.
            "primary_predictions": [
                item.as_dict() for item in baseline_predictions
            ],
            "primary_classification_source": "generic MUSK baseline",
            "evidence": [item.as_dict() for item in evidence],
            "synthesis": structured,
            "raw_synthesis": raw if structured is None else "",
            "llm_model": model,
            "prompt_generation_prompt": prompt_generation_request,
            "review_prompt": review_prompt,
            "notice": "Research prototype only. Not validated for clinical use or patient care.",
        }

