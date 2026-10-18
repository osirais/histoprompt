from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from .clinical_workflow import (
    PROMPT_BUILDER_SYSTEM,
    REVIEW_SYSTEM_PROMPT,
    _extract_prompts,
    _generic_prompt,
    _json_from_model,
    build_prompt_generation_request,
    build_review_request,
    format_evidence,
    normalize_review_classification,
)
from .config import Settings
from .hosted_backend import (
    MODEL_NAMES,
    HostedModelError,
    make_benchmark_backend,
)
from .lumen import LumenClient
from .musk_backend import MuskError
from .rag import EvidenceIndex


def _configured_models(settings: Settings) -> list[str]:
    models = ["musk"]
    if getattr(settings, "conch_backend", "disabled") == "remote":
        models.append("conch")
    for model in ("quiltnet", "plip"):
        if (
            getattr(settings, f"{model}_endpoint", "")
            and getattr(settings, f"{model}_api_key", "")
        ):
            models.append(model)
    return models


def _classify_model(
    settings: Settings,
    model: str,
    image: str,
    baseline_prompts: dict[str, str],
    enhanced_prompts: dict[str, str],
) -> tuple[str, dict[str, Any]]:
    try:
        backend = make_benchmark_backend(settings, model)
        baseline = backend.classify(image, baseline_prompts)
        enhanced = backend.classify(image, enhanced_prompts)
        return model, {
            "name": MODEL_NAMES[model],
            "baseline": baseline[0].as_dict() if baseline else None,
            "enhanced": enhanced[0].as_dict() if enhanced else None,
            "error": "",
        }
    except (HostedModelError, MuskError) as exc:
        return model, {
            "name": MODEL_NAMES[model],
            "baseline": None,
            "enhanced": None,
            "error": str(exc),
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
        evidence_text = format_evidence(evidence)
        prompt_generation_request = build_prompt_generation_request(
            report, labels, evidence_text
        )
        requested_model = str(payload.get("model", ""))
        raw_prompt_plan, prompt_model = self.lumen.complete(
            PROMPT_BUILDER_SYSTEM,
            prompt_generation_request,
            requested_model,
        )
        musk_prompts = _extract_prompts(_json_from_model(raw_prompt_plan), labels)
        generic_prompts = {label: _generic_prompt(label) for label in labels}
        models = _configured_models(self.settings)
        unordered_results: dict[str, dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=len(models)) as pool:
            futures = {
                pool.submit(
                    _classify_model,
                    self.settings,
                    model_name,
                    image,
                    generic_prompts,
                    musk_prompts,
                ): model_name
                for model_name in models
            }
            for future in as_completed(futures):
                model_name, result = future.result()
                unordered_results[model_name] = result
        model_results = {
            model_name: unordered_results[model_name] for model_name in models
        }
        if not any(result["enhanced"] for result in model_results.values()):
            errors = "; ".join(
                result["error"] for result in model_results.values() if result["error"]
            )
            raise MuskError(errors or "No configured vision model returned a result.")
        review_prompt = build_review_request(
            report=report,
            labels=labels,
            prompts=musk_prompts,
            model_results=model_results,
            evidence_text=evidence_text,
        )
        raw, model = self.lumen.complete(
            REVIEW_SYSTEM_PROMPT,
            review_prompt,
            prompt_model,
        )
        structured = _json_from_model(raw)
        final_classification = normalize_review_classification(structured, labels)
        musk_result = model_results.get("musk", {})
        conch_result = model_results.get("conch", {})
        baseline_predictions = (
            [musk_result["baseline"]] if musk_result.get("baseline") else []
        )
        enhanced_predictions = (
            [musk_result["enhanced"]] if musk_result.get("enhanced") else []
        )
        return {
            "musk_prompts": musk_prompts,
            "case_specific_prompts": musk_prompts,
            "primary_prompts": musk_prompts,
            "model_results": model_results,
            "baseline_predictions": baseline_predictions,
            "musk_predictions": enhanced_predictions,
            "evidence_predictions": enhanced_predictions,
            "conch_predictions": (
                [conch_result["enhanced"]] if conch_result.get("enhanced") else []
            ),
            "primary_predictions": enhanced_predictions,
            "primary_classification_source": "case-specific Lumen prompt with MUSK",
            "evidence": [item.as_dict() for item in evidence],
            "review": structured,
            "synthesis": structured,
            "final_classification": final_classification,
            "raw_synthesis": raw if structured is None else "",
            "llm_model": model,
            "prompt_generation_prompt": prompt_generation_request,
            "review_prompt": review_prompt,
            "notice": "Research prototype only. Not validated for clinical use or patient care.",
        }

