# PathGen clinician-workflow benchmark

This is the primary end-to-end HistoPrompt benchmark. It runs every materialized PathGen case through the same information flow intended for the interactive application:

1. Supply one pathology image, its simulated case report, and all eight candidate diagnoses.
2. Retrieve relevant passages from the frozen local evidence corpus using the report and candidates.
3. Ask Lumen for a separate case-specific microscopic description for every candidate.
4. Classify the same image with both label-only and case-specific prompts using MUSK, CONCH, QuiltNet, and PLIP.
5. Ask Lumen to review the report, retrieved evidence, generated prompts, and all model outputs.
6. Compare each image-model result and the final Lumen classification with the frozen PathGen project label.

There is no offline prompt tuning, template selection, or reuse of the PathGen ground-truth label in either Lumen request. PathGen's generated caption is used as the simulated report because this materialized collection does not include an authentic clinician report. Each saved case record preserves the exact report, evidence, prompts, scores, and review.

## Run every case

From the repository root on Delta, with Lumen and all four hosted pathology-model credentials in the ignored `.env.local` file:

```bash
python3 scripts/run_pathgen_clinical_workflow.py \
  --workers 8 \
  --resume \
  --output-dir benchmarks/pathgen-clinical-workflow
```

The runner verifies every image and report checksum before use. Completed cases are stored individually under `cases/`, so rerunning with `--resume` skips only records produced by the exact same workflow fingerprint. That fingerprint includes the candidate labels, model list, retrieval setting, evidence-corpus checksum, and relevant source-code checksums.

For a quick structural check before a full run:

```bash
python3 scripts/run_pathgen_clinical_workflow.py \
  --per-project 1 \
  --workers 4 \
  --output-dir benchmarks/pathgen-clinical-workflow-smoke
```

To rebuild the readable report from the saved, checksum-bound case records without calling Lumen or any hosted vision model:

```bash
python3 scripts/run_pathgen_clinical_workflow.py \
  --report-only \
  --output-dir benchmarks/pathgen-clinical-workflow
```

## Outputs

- `cases/<case_id>.json`: complete auditable input and output for one case;
- `results.json`: configuration receipt, workflow fingerprint, and aggregate metrics;
- `RESULTS.md`: readable overall and organ-by-model baseline, prompt-enhanced, paired-change, and final-review comparison;
- `failures.json`: cases requiring a resumed retry, created only when a run is incomplete.

Image-model accuracy and final-review accuracy are intentionally separate. Some generated PathGen reports explicitly name an organ or suspected diagnosis, so the final review has more information than the image models and should not be presented as image-only performance.
