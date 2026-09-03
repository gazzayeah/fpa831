"""
Local RAG over ``docs/finance_rag_corpus/``.

v1 is keyword overlap plus status boosts (current > superseded). ADV-001/002
stay in the index so retrieval tests can prove they are handled as untrusted
or irrelevant. Swap this module later for Vertex RAG Engine without changing
the retrieve_finance_documents tool contract.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from financial_processing_agent.shared_libraries.settings import settings


@dataclass
class CorpusChunk:
    """One markdown policy or attachment after YAML front matter is parsed."""
    document_id: str
    title: str
    version: str
    status: str
    document_type: str
    text: str
    path: str


def _parse_front_matter(raw: str) -> tuple[dict[str, str], str]:
    """Split ``---`` YAML-like headers into a string map and body."""
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    meta: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, parts[2]


def load_corpus(corpus_dir: Path | None = None) -> list[CorpusChunk]:
    """Index every ``*.md`` file; ``document_id`` comes from front matter."""
    root = corpus_dir or settings.resolved_corpus_dir
    chunks: list[CorpusChunk] = []
    for path in sorted(root.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = _parse_front_matter(raw)
        chunks.append(
            CorpusChunk(
                document_id=meta.get("document_id", path.stem),
                title=meta.get("title", path.stem),
                version=meta.get("version", ""),
                status=meta.get("status", "current"),
                document_type="policy" if meta.get("document_id", "").startswith("FIN-POL") else "attachment",
                text=body.strip(),
                path=str(path),
            )
        )
    return chunks


def _tokens(text: str) -> set[str]:
    """Lowercase alphanumeric tokens longer than two characters."""
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2}


def search_corpus(query: str, *, top_k: int = 8, corpus_dir: Path | None = None) -> list[dict]:
    """
    Rank chunks for a query using token overlap plus status boosts.

    Scoring (higher is better):
        overlap count + 20 if document_id appears in the query
        +3 if status is current, −8 if superseded, +0.5 if untrusted (ADV-001
        stays retrievable so FIN-003 can prove it is handled, not hidden).

    Returns a list of citation-shaped dicts (document_id, snippet, relevance, …).
    """
    chunks = load_corpus(corpus_dir)
    query_tokens = _tokens(query)
    scored: list[tuple[float, CorpusChunk]] = []
    for chunk in chunks:
        overlap = len(query_tokens & _tokens(chunk.title + " " + chunk.text + " " + chunk.document_id))
        score = float(overlap)
        if chunk.document_id.lower() in query.lower():
            score += 20
        if chunk.status == "current":
            score += 3
        if chunk.status == "superseded":
            score -= 8
        if chunk.status == "untrusted":
            score += 0.5
        scored.append((score, chunk))
    scored.sort(key=lambda item: (-item[0], item[1].document_id))
    results = []
    for score, chunk in scored[:top_k]:
        snippet = chunk.text.replace("\n", " ")[:280]
        results.append(
            {
                "document_id": chunk.document_id,
                "title": chunk.title,
                "version": chunk.version,
                "status": chunk.status,
                "document_type": chunk.document_type,
                "page": "1",
                "relevance": score,
                "snippet": snippet,
            }
        )
    return results
