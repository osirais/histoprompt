import json

from ashby.rag import EvidenceIndex


def test_retrieval_ranks_matching_marker_document(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    documents = [
        {"source_id": "a", "title": "Lung markers", "text": "TTF-1 and Napsin A support lung adenocarcinoma."},
        {"source_id": "b", "title": "Unrelated", "text": "Melanoma follow-up outcomes."},
    ]
    corpus.write_text("\n".join(json.dumps(item) for item in documents), encoding="utf-8")
    results = EvidenceIndex(corpus).search("TTF-1 Napsin lung", limit=2)
    assert results[0].source_id == "a"
    assert results[0].score > 0


def test_retrieval_ignores_nonmatching_documents(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(
        json.dumps({"source_id": "a", "title": "Lung", "text": "adenocarcinoma"}),
        encoding="utf-8",
    )
    assert EvidenceIndex(corpus).search("melanoma") == []

