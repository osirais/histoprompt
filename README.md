# HistoPrompt

HistoPrompt is a research prototype that improves the text prompts sent to the official [MUSK pathology vision-language model](https://github.com/lilab-stanford/MUSK). It uses a de-identified report and a frozen local evidence corpus to create visually specific descriptions for every candidate label before MUSK sees the image.

The live path is:

1. Search the local evidence corpus using the report and candidate labels.
2. Ask Lumen to turn the report and retrieved evidence into case-specific histopathology prompts.
3. Send the image and enriched prompts through an SSH tunnel to the hackathon MUSK server on Delta.
4. Ask Lumen to compare MUSK's result with the report and evidence and produce a structured human-review summary.

This is not a diagnostic device and must not be used for patient care. Upload only de-identified material. The bundled corpus is a small demonstration set, not a clinically adequate knowledge base. Prompt enrichment is a hypothesis; improved accuracy must be established against a labeled baseline.

## Quick start

You need an NCSA account with Delta access, Duo, [Git](https://git-scm.com/), and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone git@github.com:osirais/histoprompt.git
cd histoprompt
cp .env.example .env.local
```

Edit `.env.local` and fill in your Delta username:

```dotenv
DELTA_USERNAME=your_ncsa_username
```

Then use two terminals:

```bash
# Terminal 1: complete the NCSA password and Duo prompts, then leave it open
./scripts/start_delta_tunnel.sh

# Terminal 2
./run.sh
```

Open <http://127.0.0.1:8787>. The status strip should show MUSK, Lumen, and the evidence corpus as ready before analysis.

The shared MUSK host, event-wide bearer key, and current Lumen key are bundled in `.env.example` by request so the private-repo clone works immediately. The hosted MUSK service is expected to stop working Sunday at 6 PM. Rotate or remove the committed credentials after the event.

## What it adds to MUSK

Plain MUSK receives label-only prompts such as `herpes simplex esophagitis`. HistoPrompt can instead send a description such as `ulcerated squamous mucosa with multinucleation, nuclear molding, chromatin margination, and intranuclear inclusions`. The result page exposes every generated prompt, the MUSK result, retrieved sources, discrepancies, and recommended human review.

The hosted hackathon service returns only its highest-ranked candidate per image. HistoPrompt therefore treats the score as model output to review, not calibrated diagnostic confidence.

## Hosted MUSK on Delta

The opening-session setup exposes MUSK only inside Delta. `scripts/start_delta_tunnel.sh` maps the service to `http://127.0.0.1:8801` on your laptop; HistoPrompt calls the server's `/health` and `/classify` routes using the official hackathon schema.

Everyone should still accept the MUSK terms on Hugging Face as requested by the organizers, but the default hosted path does not download model weights to the laptop.

## Optional local MUSK fallback

After the hosted service expires, HistoPrompt can load the official `xiangjx/musk` weights directly. Accept the gated model terms on Hugging Face, then configure:

```dotenv
MUSK_BACKEND=local
MUSK_DEVICE=auto
HF_TOKEN=hf_...
```

Run `./run.sh`; it installs the additional pinned model dependencies automatically. The first request loads MUSK lazily. `MUSK_DEVICE=auto` selects CUDA, Apple Silicon MPS, or CPU in that order.

## Evidence corpus

The application reads JSON Lines records with `source_id`, `title`, `text`, and optional `year` and `url` fields. The demonstration corpus includes lung differential-diagnosis sources, infectious-esophagitis sources, and the MUSK paper.

To build another frozen corpus from PubMed identifiers:

```bash
python3 scripts/build_corpus.py 22966403 26447895 26137020 \
  --output data/corpus.local.jsonl
```

Then set `HISTOPROMPT_CORPUS=data/corpus.local.jsonl`. Corpus preparation may use the internet, but runtime retrieval is local. The configured MUSK and Lumen services remain remote.

## Tests

```bash
uv run pytest
```

Tests cover retrieval, structured response parsing, prompt enrichment order, fallback prompts, and the NCSA MUSK request schema. GitHub Actions does not download the gated checkpoint or call live services.

## Multi-disease prompt benchmark

The repository includes a fixed 34-image engineering benchmark spanning lung cancer, colon cancer, infectious esophagitis, and skin cancer. It compares label-only, generic histology, hand-curated morphology, and locally retrieved evidence converted into morphology prompts by Lumen. Evidence prompts are generated once per candidate family and never receive a report, image contents, or the correct label.

With the Delta tunnel open, run:

```bash
uv run python scripts/run_benchmark.py
```

The exact benchmark images are stored in `benchmarks/images/`. The manifest records a SHA-256 checksum for every image, and the runner verifies it before inference. This lets another model receive the same image bytes later. Source, selection, and license details are in `benchmarks/images/SOURCES.md`.

The runner writes auditable raw output to `benchmarks/results/latest.json` plus a readable comparison to `benchmarks/results/latest.md`. This remains an engineering benchmark, not clinical validation: sample counts are small, each task has a tissue-specific candidate list, and the hosted API exposes only its winning label and score.
