"""Map retriever chunk dicts onto the Citation schema used in RunState."""

from __future__ import annotations

from financial_processing_agent.shared_libraries.schemas import Citation


def citation_from_chunk(chunk: dict) -> Citation:
    """Build a Citation; snippet is truncated for logs and prompts."""
    return Citation(
        document_id=chunk.get("document_id", ""),
        document_type=chunk.get("document_type", "policy"),
        version=str(chunk.get("version", "")),
        page=str(chunk.get("page", "")),
        relevance=float(chunk.get("relevance", 0.0)),
        status=chunk.get("status", "current"),
        snippet=chunk.get("snippet", "")[:280],
        title=chunk.get("title", ""),
    )
