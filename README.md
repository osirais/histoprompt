# Ashby

Ashby is a hackathon prototype that adds an evidence-grounded review layer on top of the official [MUSK pathology vision-language model](https://github.com/lilab-stanford/MUSK).

The browser app runs on your laptop. Image classification goes through an SSH tunnel to the hackathon's MUSK server on Delta, evidence retrieval stays local, and Lumen writes the structured review. The browser never receives either API key.

This is not a diagnostic device and must not be used for patient care. Upload only de-identified material. The bundled corpus is a small demonstration set, not a clinically adequate knowledge base.

## Quick start

You need an NCSA account with Delta access, Duo, a Lumen key, [Git](https://git-scm.com/), and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone git@github.com:osirais/ashby.git
cd ashby
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

The shared MUSK host, event-wide bearer key, and current Lumen key are bundled in `.env.example` by request so the private-repo clone works immediately. The MUSK service is expected to stop working Sunday at 6 PM. Rotate or remove the committed credentials after the event.

## Lumen configuration

Create an API key on the [Lumen profile page](https://lumen.ncsa.illinois.edu/profile). A key only sees models whose notices have been acknowledged in Lumen.

```dotenv
LUMEN_API_KEY=sk_...
LUMEN_BASE_URL=https://lumen.ncsa.illinois.edu/v1
LUMEN_MODEL=<exact model id from GET /v1/models>
```

Keep `.env.local` local; it is ignored by Git. The browser never receives the key.

## Hosted MUSK on Delta

The opening-session setup exposes MUSK only inside Delta. `scripts/start_delta_tunnel.sh` maps the service to `http://127.0.0.1:8801` on your laptop; Ashby calls the server's `/health` and `/classify` routes using the official hackathon request schema.

Everyone should still accept the MUSK terms on Hugging Face as requested by the organizers, but the default hosted path does not download model weights to the laptop.

## Optional local MUSK fallback

After the hosted service expires, Ashby can load the official `xiangjx/musk` weights directly. Accept the gated model terms on Hugging Face, then configure:

```dotenv
MUSK_BACKEND=local
MUSK_DEVICE=auto
HF_TOKEN=hf_...
```

Run `./run.sh`; it installs the additional pinned model dependencies automatically. MUSK loads lazily on the first request, so the first analysis is slower. The code follows the upstream zero-shot flow: 384-pixel preprocessing, the MUSK retrieval heads, normalized image/text embeddings, and softmax over the candidate labels.

The upstream dependency pins PyTorch 2.0.1 and targets Python 3.10. `MUSK_DEVICE=auto` selects CUDA, Apple Silicon MPS, or CPU in that order. CPU inference is supported for smoke testing but will be slow.

## Replace or expand the evidence corpus

The application reads JSON Lines records with `source_id`, `title`, `text`, and optional `year` and `url` fields. To build a frozen local corpus from PubMed identifiers:

```bash
python3 scripts/build_corpus.py 22966403 26447895 26137020 \
  --output data/corpus.local.jsonl
```

Then set `ASHBY_CORPUS=data/corpus.local.jsonl`. This fetch happens during corpus preparation only. The live request path remains local except for whichever model endpoints you configure.

## Tests

```bash
uv run pytest
```

GitHub Actions runs the dependency-light retrieval and response-parsing tests on every push. It deliberately does not download the gated MUSK checkpoint or call Lumen.


