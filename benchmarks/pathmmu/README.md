# PathMMU benchmark

Status: blocked on separate Hugging Face dataset approval.

PathMMU is the planned broad-organ benchmark for HistoPrompt. It was built to evaluate pathology image understanding and reasoning, rather than segmentation or tissue-of-origin classification.

## Why it matches

Each benchmark item contains a pathology image, a question, candidate answers, the correct answer, and an explanation. The official validation and test material was reviewed by pathologists. The dataset covers multiple organ systems and pathology specialties across PubMed, expert social-media posts, educational material, atlases, and established classification datasets.

Official resources:

- Dataset: <https://huggingface.co/datasets/jamessyx/PathMMU>
- Paper: <https://arxiv.org/abs/2401.16355>
- Evaluation code: <https://github.com/PathMMU-Benchmark/PathMMU>

## Access required

1. Sign in to Hugging Face.
2. Open the official dataset page.
3. Complete the linked access form and accept the dataset terms. The form email must match the Hugging Face account email.
4. Wait for approval; the maintainers state that processing normally takes one to two days.
5. Create a Hugging Face read token and save it locally as `HF_TOKEN` in `.env.local`. Never commit it.

MUSK model approval and PathMMU dataset approval are separate.

## Planned comparison

For each question, candidate answer choices become the labels that the hosted pathology encoder ranks.

1. **Original:** score the image against a fixed prompt containing the question and each answer choice.
2. **Enhanced:** retrieve evidence from a frozen corpus and ask Lumen to write a concise, visually grounded phrase for each answer choice. Score the same image against those phrases.
3. **Reasoning layer:** give Lumen the question, ranked model output, and retrieved evidence, then score its final answer against the official answer.

The correct answer and official explanation stay hidden until scoring. They are never provided to retrieval, Lumen prompt generation, or the image encoder.

## Evaluation protocol

- Develop prompt wording on the official validation split only.
- Evaluate once on the official test split.
- Report overall accuracy and accuracy by official source subset.
- Add a frozen, auditable organ-system mapping before claiming balanced organ coverage.
- Compare original and enhanced predictions per item, including fixed and broken answers.
- Record the dataset revision, sample IDs, prompts, checksums, runtime, and every raw prediction.
- Evaluate the Lumen reasoning layer separately from image-encoder accuracy.

No PathMMU images or questions are currently stored in this repository.
