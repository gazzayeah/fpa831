"""RAG tool: ranked chunks with document_id, type, version, relevance, citation metadata."""

from __future__ import annotations

from financial_processing_agent.utils.citations import citation_from_chunk
from financial_processing_agent.utils.corpus import search_corpus
from financial_processing_agent.utils.injection import scan_untrusted_text


def retrieve_finance_documents(query: str, top_k: int = 8) -> dict:
    """
    Search the finance policy corpus.

    Returns ``{"chunks": [Citation dicts plus injection_flags]}``. ADV-001/002
    appear only when the query names them or already contains injection
    language. ``injection_flags`` on a chunk is empty unless the snippet
    itself matches ``utils/injection.py`` (so ADV-002 is untrusted, not an
    override).
    """
    chunks = search_corpus(query, top_k=top_k)
    citations = []
    for chunk in chunks:
        payload = citation_from_chunk(chunk).model_dump()
        # Empty on ADV-002: untrusted status is not an injection flag.
        payload["injection_flags"] = scan_untrusted_text(chunk.get("snippet", ""))
        citations.append(payload)
    return {"chunks": citations}
