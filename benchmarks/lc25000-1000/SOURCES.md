# LC25000 1,000-image benchmark source

- Source mirror: [1aurent/LC25000](https://huggingface.co/datasets/1aurent/LC25000), commit `2387ffed63932faa8fd05c679ffec85fc3153f61`
- Original dataset: [tampapath/lung_colon_image_set](https://github.com/tampapath/lung_colon_image_set)
- License recorded by the Hugging Face dataset card: Unlicense
- Classes: benign lung, lung adenocarcinoma, lung squamous cell carcinoma, benign colon, and colorectal adenocarcinoma
- Selection: every 25th row within each class, producing exactly 200 images per class and 1,000 images total

Selection is deterministic and happens before inference. The manifest records each image's dataset row, within-class rank, source Parquet shard, source filename, repository path, and SHA-256 checksum.

LC25000 was created by augmenting a smaller set of original tissue images. Therefore, this benchmark is balanced by dataset class but is not patient-independent and must not be treated as clinical validation.
