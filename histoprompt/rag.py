from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+.-]*", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


@dataclass(frozen=True)
class Evidence:
    source_id: str
    title: str
    text: str
    url: str = ""
    year: str = ""
    score: float = 0.0

    def as_dict(self) -> dict[str, str | float]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "text": self.text,
            "url": self.url,
            "year": self.year,
            "score": round(self.score, 4),
        }


class EvidenceIndex:
    """Small, dependency-free BM25 index over a frozen local corpus."""

    def __init__(self, corpus_path: Path):
        self.documents = self._load(corpus_path)
        if not self.documents:
            raise ValueError(f"No evidence documents found in {corpus_path}")
        self.tokens = [tokenize(f"{doc.title} {doc.text}") for doc in self.documents]
        self.lengths = [len(tokens) for tokens in self.tokens]
        self.average_length = sum(self.lengths) / max(len(self.lengths), 1)
        self.frequencies = [Counter(tokens) for tokens in self.tokens]
        document_frequency: Counter[str] = Counter()
        for tokens in self.tokens:
            document_frequency.update(set(tokens))
        total = len(self.documents)
        self.idf = {
            token: math.log(1 + (total - count + 0.5) / (count + 0.5))
            for token, count in document_frequency.items()
        }

    @staticmethod
    def _load(path: Path) -> list[Evidence]:
        documents: list[Evidence] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not item.get("source_id") or not item.get("title") or not item.get("text"):
                raise ValueError(f"Invalid corpus record at {path}:{line_number}")
            documents.append(
                Evidence(
                    source_id=str(item["source_id"]),
                    title=str(item["title"]),
                    text=str(item["text"]),
                    url=str(item.get("url", "")),
                    year=str(item.get("year", "")),
                )
            )
        return documents

    def search(self, query: str, limit: int = 5) -> list[Evidence]:
        query_counts = Counter(tokenize(query))
        k1 = 1.5
        b = 0.75
        scored: list[tuple[float, int]] = []
        for index, frequencies in enumerate(self.frequencies):
            score = 0.0
            length = self.lengths[index]
            for token, query_count in query_counts.items():
                frequency = frequencies.get(token, 0)
                if not frequency:
                    continue
                numerator = frequency * (k1 + 1)
                denominator = frequency + k1 * (
                    1 - b + b * length / max(self.average_length, 1)
                )
                score += self.idf.get(token, 0.0) * numerator / denominator
                score *= 1 + math.log(query_count)
            if score > 0:
                scored.append((score, index))
        scored.sort(reverse=True)
        return [
            Evidence(**{**self.documents[index].__dict__, "score": score})
            for score, index in scored[: max(1, min(limit, 12))]
        ]

