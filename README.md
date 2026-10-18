# HistoPrompt

HistoPrompt is a research prototype that tests whether better text prompts can improve the official [MUSK pathology vision-language model](https://github.com/lilab-stanford/MUSK). It uses a de-identified report and a frozen local evidence corpus to create visually specific descriptions for every candidate label before MUSK sees the image.

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
./scripts/setup.sh
```

The setup asks for a Lumen API key and either the hosted MUSK credentials or a Hugging Face token for local MUSK. It saves them only in the ignored `.env.local` file. Credentials are not included in Git, even for a private repository.

Then use two terminals:

```bash
# Terminal 1: complete the NCSA password and Duo prompts, then leave it open
./scripts/start_delta_tunnel.sh

# Terminal 2
./run.sh
```

Open <http://127.0.0.1:8787>. The status strip should show MUSK, Lumen, and the evidence corpus as ready before analysis.

The hosted path requires three things that cannot be created by cloning: an NCSA account with Delta access, a Lumen API key, and the shared MUSK bearer key. Obtain those separately from the project owner or event organizers. The setup script reports any missing value before starting the app.

## What it adds to MUSK

Plain MUSK receives label-only prompts such as `herpes simplex esophagitis`. The validated primary template is the short `histology showing {label}` form: on the fixed 600-image lung benchmark it scored 556/600 (92.7%), versus 538/600 (89.7%) for the generic template. HistoPrompt still exposes longer appended and evidence-generated prompts for experimentation, but those are not promoted unless they beat the short template on held-out data.

The hosted hackathon service returns only its highest-ranked candidate per image. HistoPrompt therefore treats the score as model output to review, not calibrated diagnostic confidence.

## Optional NCSA CONCH comparison

The hackathon also provides CONCH as a separate hosted service on Delta. It uses the same `/classify` request shape as MUSK, but has a separate host, port, and bearer key. The app keeps MUSK as the primary result and displays CONCH as an optional comparison when enabled.

Accept the gated [CONCH model terms](https://huggingface.co/MahmoodLab/CONCH) yourself, then put the host and key supplied in the hackathon Slack channel into `.env.local`:

```dotenv
CONCH_BACKEND=remote
CONCH_ENDPOINT=http://127.0.0.1:8802
CONCH_API_KEY=your_private_conch_key
DELTA_CONCH_HOST=the_conch_host_from_slack
DELTA_CONCH_PORT=8002
CONCH_TUNNEL_PORT=8802
```

Restart `scripts/start_delta_tunnel.sh`; it forwards both services through the same SSH session. `CONCH_BACKEND=disabled` leaves the MUSK-only path unchanged.

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

### Large batched benchmark

The repository also stores a deterministic, balanced 1,000-image LC25000 collection. The completed comparison uses its 600-image lung subset: 200 benign lung images, 200 lung adenocarcinoma images, and 200 lung squamous-cell carcinoma images. Run the same comparison with:

```bash
uv run python scripts/run_benchmark.py \
  --manifest benchmarks/lc25000-600/manifest.json \
  --output-dir benchmarks/lc25000-600/results \
  --batch-size 32 \
  --strategies generic evidence_generated
```

Batching reduced measured MUSK time to 0.391 seconds per image and prompt strategy. In the saved run, Original MUSK scored 538/600 (89.7%) and Enhanced MUSK scored 478/600 (79.7%). See `benchmarks/lc25000-600/results/latest.md` for the label-level breakdown and limitations.
