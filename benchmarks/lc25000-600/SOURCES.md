# LC25000 600-image lung benchmark source

This is the lung-only subset of the repository's fixed 1,000-image LC25000 collection. It contains 200 images for each of three labels: benign lung tissue, lung adenocarcinoma, and lung squamous cell carcinoma.

- Source mirror: [1aurent/LC25000](https://huggingface.co/datasets/1aurent/LC25000), commit `2387ffed63932faa8fd05c679ffec85fc3153f61`
- Original dataset: [tampapath/lung_colon_image_set](https://github.com/tampapath/lung_colon_image_set)
- License recorded by the Hugging Face dataset card: Unlicense
- Selection: every 25th row within each class, fixed before inference
- Image storage: `benchmarks/lc25000-1000/images/`; the 600-image manifest points to those same exact files rather than duplicating them

LC25000 contains augmented derivatives of a smaller original collection. The benchmark is balanced by class but is not patient-independent and must not be treated as clinical validation.
