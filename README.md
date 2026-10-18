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

Plain MUSK receives label-only prompts such as `herpes simplex esophagitis`. Prompt wording can improve a fixed task,
but it is model- and dataset-specific: a short template improved MUSK on the 600-image lung benchmark, while the
independently selected MUSK template was 1.4 points worse on the broader PathGen stress test. HistoPrompt therefore
keeps enriched prompts experimental and reports them beside the original prompt rather than treating them as a
universal upgrade.

The hosted hackathon service returns only its highest-ranked candidate per image. HistoPrompt therefore treats the score as model output to review, not calibrated diagnostic confidence.

## Optional NCSA CONCH comparison

The hackathon also provides CONCH as a separate hosted service on Delta. It uses the same `/classify` request shape as MUSK, but has a separate host, port, and bearer key. The app keeps MUSK as the primary result and displays CONCH as an optional comparison when enabled.

Accept the gated [CONCH model terms](https://huggingface.co/MahmoodLab/CONCH) yourself, then put the host and key supplied in the hackathon Slack channel into `.env.local`:

```dotenv
CONCH_BACKEND=remote
CONCH_ENDPOINT=http://127.0.0.1:8802
CONCH_API_KEY=your_private_conch_key
DELTA_CONCH_HOST=the_conch_host_from_slack
DELTA_CONCH_PORT=8000
CONCH_TUNNEL_PORT=8802
```

Restart `scripts/start_delta_tunnel.sh`; it forwards both services through the same SSH session. `CONCH_BACKEND=disabled` leaves the MUSK-only path unchanged.

The same tunnel can also forward QuiltNet and PLIP when their host values are present in `.env.local` (local ports `8803` and `8804`). Run `source .env.local && ./scripts/check_model_services.sh` for a quick health check of all four services.

## Validated prompt tuning (lung)

`scripts/tune_prompts.py` searches 33 sourced base templates independently for MUSK, CONCH, QuiltNet, or PLIP. A
candidate replaces the starting template only if it gains at least 1 point on tuning, passes a paired one-sided sign
test, and gains at least 0.5 point on a separate confirmation set. The model-specific prompt is then frozen before
held-out testing. Method, prompts, raw selection logs, and reproduction details are in
[`benchmarks/lc25000-tuning/`](benchmarks/lc25000-tuning/README.md).

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

## Benchmarks

The organized benchmark entry point is [`benchmarks/README.md`](benchmarks/README.md), and the current human-readable comparison is [`benchmarks/RESULTS.md`](benchmarks/RESULTS.md).

The current automated suite reruns the fixed 11-label diagnosis smoke test across MUSK, CONCH, QuiltNet, and PLIP and regenerates the aggregate report:

```bash
uv run python scripts/run_benchmark_suite.py
```

The repository also keeps separate suites for 11 diagnosis labels, individually tuned lung prompts, a 1,000-image lung-and-colon stress set, and the original 600-image RAG comparison. Exploratory prompt screens and the invalid shared-prompt cross-model experiment are clearly archived.

On NCSA, the complete materialized PathGen suite evaluates all 2,141 available PNGs with original and independently
selected prompts across all four hosted models:

```bash
uv run python scripts/run_pathgen_ncsa_suite.py --batch-size 8 --workers 4 --resume
```

See the [full PathGen comparison](benchmarks/pathgen-ncsa/RESULTS.md) and
[reproduction notes](benchmarks/pathgen-ncsa/README.md).

Every active suite stores or identifies fixed source images, records SHA-256 checksums, and keeps raw JSON beside readable Markdown. `scripts/run_benchmark_suite.py` reruns the current suite and regenerates the aggregate report. These are engineering benchmarks, not clinical validation.

The next broad benchmark is PathMMU, which was designed for pathology image understanding and reasoning across multiple organ systems and specialties. It requires separate dataset approval; MUSK model access is not sufficient. The discarded PanNuke experiment is not included because tissue-origin labels do not test HistoPrompt's diagnosis and reasoning workflow.
