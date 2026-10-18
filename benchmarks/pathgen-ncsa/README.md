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

The per-model selection method was audited at branch tip `81f8c99` from the implementation in commit `00f498b`.
That branch predated the repository's four-model benchmark runner, so its selection algorithm was ported into
current `main` instead of replacing newer multi-model work with the older MUSK-only runner. The port preserves the
branch's 33-template search, Lumen phrase-generation stage, and acceptance gates while running them separately for
each hosted model.

1. Select a base template independently for each model using the separate LC25000 tuning set.
2. Ask Lumen for short, label-specific visible morphology phrases, then score every candidate against that same model.
3. For both stages, require at least a 1-point tuning gain, paired one-sided sign-test `p < 0.05`, and at least a
   0.5-point gain on the separate confirmation set before accepting a change.
4. Freeze the selected template and accepted phrases before opening PathGen results.
5. Verify each original PNG against its frozen SHA-256, then remove EXIF, ICC-profile, and text metadata chunks
   before upload. The compressed pixel chunks are unchanged; this avoids decoder failures from oversized metadata.
6. On all 2,141 PathGen tiles, compare the original prompt, selected base template, and fully tuned prompt set.
7. Report tile accuracy, macro project accuracy, each project, each slide, confusion counts, paired fixes/breaks,
   runtime, checksums, and completeness.

The PathGen set is evaluation-only. No PathGen result is used to choose a template or phrase.

The supplied tuning data covers only three lung labels. Therefore the fully tuned condition can apply accepted phrases
to PathGen's lung adenocarcinoma and lung squamous-cell carcinoma labels; the remaining six labels use the selected
base template. The report states this coverage explicitly rather than calling those six labels phrase-tuned.

## Reproduce on NCSA

From the repository root on a Delta login node or CPU job, with the four internal endpoints and bearer keys in the
ignored `.env.local` file:

```bash
uv run python scripts/run_pathgen_ncsa_suite.py --batch-size 8 --workers 4 --resume
```

The command verifies and rebuilds `manifest.json`, resumes interrupted per-model work, and writes the four raw result
files plus `RESULTS.md`.

To rebuild only the readable aggregate after the four per-model files already exist:

```bash
uv run python scripts/run_pathgen_ncsa_suite.py --report-only
```

## Interpretation boundary

This is a tile-level engineering benchmark, not clinical validation. Its 2,141 tiles come from only 10 slides, so
they are correlated observations rather than 2,141 independent patients. TCGA project recognition also combines
tissue identity and cancer morphology; it is not unrestricted diagnosis. Some project distinctions, particularly
colon versus rectal adenocarcinoma, cannot be expected to be reliable from an isolated patch.
