# HistoPrompt slides

This directory contains the source and embedded assets for the hackathon deck.
The build creates the canonical PowerPoint file at
`output/slides/HistoPrompt_Hackathon_Deck.pptx`.

## Build the PowerPoint deck

```sh
/Users/orlan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
  slides/build.mjs
```

## Export the PDF

```sh
mkdir -p output/pdf
soffice --headless --convert-to pdf --outdir output/pdf \
  output/slides/HistoPrompt_Hackathon_Deck.pptx
```

`histoprompt_visuals.py` is the Manim source for the four full-slide visualizations.
The exact rendered frames used by the deck are stored in `slides/assets`, so Manim
is not required for a normal rebuild.
