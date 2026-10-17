from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .config import Settings
from .lumen import LumenClient
from .musk_backend import make_musk_backend
from .rag import EvidenceIndex


SYSTEM_PROMPT = """You are the evidence-review layer in a research-only computational pathology prototype.
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

        predictions = make_musk_backend(self.settings).classify(image, labels)
        query = " ".join([report, *[item.label for item in predictions[:5]]])
        evidence = self.evidence_index.search(query, int(payload.get("top_k", 5)))
        evidence_text = "\n\n".join(
            f"[{item.source_id}] {item.title} ({item.year or 'year unknown'})\n{item.text}"
            for item in evidence
        )
        prediction_text = "\n".join(
            f"- {item.label}: {item.probability:.4f}" for item in predictions
        )
        prompt = f"""Review this case.

DE-IDENTIFIED REPORT
{report}

MUSK ZERO-SHOT SCORES
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
        raw, model = self.lumen.complete(SYSTEM_PROMPT, prompt, str(payload.get("model", "")))
        structured = _json_from_model(raw)
        return {
            "musk_predictions": [item.as_dict() for item in predictions],
            "evidence": [item.as_dict() for item in evidence],
            "synthesis": structured,
            "raw_synthesis": raw if structured is None else "",
            "llm_model": model,
            "prompt": prompt,
            "notice": "Research prototype only. Not validated for clinical use or patient care.",
        }

