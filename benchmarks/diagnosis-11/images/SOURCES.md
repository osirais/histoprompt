# Benchmark image sources

The repository stores the exact image bytes used by the benchmark. `manifest.json` records the SHA-256 checksum for each image. The runner checks each checksum before it sends an image to a hosted model.

## LC25000

- Source: [1aurent/LC25000](https://huggingface.co/datasets/1aurent/LC25000), commit `2387ffed63932faa8fd05c679ffec85fc3153f61`
- Original dataset: [tampapath/lung_colon_image_set](https://github.com/tampapath/lung_colon_image_set)
- License recorded by the Hugging Face dataset card: Unlicense
- Selection: rows 0, 1000, 2000, 3000, and 4000 within each of the five classes, before any model run
- Files: 25 original JPEG files, reproduced without image edits

LC25000 was created by augmenting a smaller set of original tissue images. The fixed spacing reduces adjacent-row selection but does not prove that all selected files come from different patients or source slides.

## Infectious esophagitis

- Source: [Educational Case: Infectious Esophagitis](https://pmc.ncbi.nlm.nih.gov/articles/PMC7005969/)
- License: Creative Commons Attribution-NonCommercial-NoDerivs 4.0
- Files: Figures 1–6, reproduced without image edits
- Labels: Candida esophagitis, herpes simplex virus esophagitis, and cytomegalovirus esophagitis

Each label has one routine H&E figure and one special-stain or immunohistochemistry figure.

## Skin cancer

- Source: [Educational Case: Basal Cell Carcinoma](https://pmc.ncbi.nlm.nih.gov/articles/PMC7944528/)
- License: Creative Commons Attribution-NonCommercial-NoDerivs 4.0
- Files: Figures 2, 4, and 5, reproduced without image edits
- Labels: basal cell carcinoma, cutaneous squamous cell carcinoma, and melanoma

These images are stored for non-commercial research evaluation in this private repository. Keep the source attribution and license notice with any copy.
