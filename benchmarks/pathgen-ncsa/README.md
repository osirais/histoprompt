# Complete materialized NCSA PathGen benchmark

This suite evaluates every PathGen image that is physically materialized in the shared NCSA hackathon collection:

- source metadata: `/projects/bfqi/shared/datasets/pathgen_dataset/PathGen-2k_samples.json`;
- pixels and generated captions: `/projects/bfqi/shared/datasets/pathgen_dataset/pathgen_2k_output`;
- verified inventory: 2,141 PNGs and 2,141 matching caption files;
- biological scope: 10 TCGA whole slides across 8 cancer projects.

The benchmark does not call the generated captions ground truth and does not give them to the models. Each tile's
label comes from the slide's TCGA project in the separately frozen full-PathGen manifest. The task is eight-way
cancer-project classification across breast, colon, kidney, brain, lung, prostate, and rectal pathology.

## Why this is called the materialized benchmark

The full PathGen metadata inventory lists 1,620,876 regions from 7,272 slides. NCSA currently provides those raw
pixels only for the 2,141-tile collection above. A larger shared store contains precomputed CONCH v1.5 embeddings,
not equivalent pixels that can be sent through MUSK, CONCH, QuiltNet, and PLIP. Therefore:

- **100% coverage in this suite** means every one of the 2,141 available PNGs;
- it does not mean that 1.62 million raw image patches were available to all four models;
- the manifest records exact checksums and refuses partial or extra materialization.

## Evaluation protocol

1. Select a base template independently for each model using the separate LC25000 tuning set.
2. Require at least a 1-point tuning gain, paired one-sided sign-test `p < 0.05`, and at least a 0.5-point gain on
   the separate confirmation set before replacing the default template.
3. Freeze the selected template before opening PathGen results.
4. On all 2,141 PathGen tiles, compare the model's original generic prompt with its selected template.
5. Report tile accuracy, macro project accuracy, each project, each slide, confusion counts, paired fixes/breaks,
   runtime, checksums, and completeness.

The PathGen set is evaluation-only. No PathGen result is used to choose a template or phrase.

## Reproduce on NCSA

From the repository root on a Delta login node or CPU job, with the four internal endpoints and bearer keys in the
ignored `.env.local` file:

```bash
uv run python scripts/run_pathgen_ncsa_suite.py --batch-size 8 --workers 4 --resume
```

The command verifies and rebuilds `manifest.json`, resumes interrupted per-model work, and writes the four raw result
files plus `RESULTS.md`.

## Interpretation boundary

This is a tile-level engineering benchmark, not clinical validation. Its 2,141 tiles come from only 10 slides, so
they are correlated observations rather than 2,141 independent patients. TCGA project recognition also combines
tissue identity and cancer morphology; it is not unrestricted diagnosis. Some project distinctions, particularly
colon versus rectal adenocarcinoma, cannot be expected to be reliable from an isolated patch.
