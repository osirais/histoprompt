from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Load a small local env file without adding a runtime dependency."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"").strip("'")
        if key:
            os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    corpus_path: Path
    lumen_api_key: str
    lumen_base_url: str
    lumen_model: str
    musk_backend: str
    musk_device: str
    musk_endpoint: str
    musk_api_key: str

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv(ROOT / ".env.local")
        _load_dotenv(ROOT / ".env")
        corpus = Path(os.getenv("ASHBY_CORPUS", "data/corpus.jsonl"))
        if not corpus.is_absolute():
            corpus = ROOT / corpus
        return cls(
            host=os.getenv("ASHBY_HOST", "127.0.0.1"),
            port=int(os.getenv("ASHBY_PORT", "8787")),
            corpus_path=corpus,
            lumen_api_key=os.getenv("LUMEN_API_KEY", ""),
            lumen_base_url=os.getenv(
                "LUMEN_BASE_URL", "https://lumen.ncsa.illinois.edu/v1"
            ).rstrip("/"),
            lumen_model=os.getenv("LUMEN_MODEL", ""),
            musk_backend=os.getenv("MUSK_BACKEND", "local").lower(),
            musk_device=os.getenv("MUSK_DEVICE", "auto"),
            musk_endpoint=os.getenv("MUSK_ENDPOINT", ""),
            musk_api_key=os.getenv("MUSK_API_KEY", ""),
        )

