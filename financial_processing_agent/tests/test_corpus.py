"""Corpus retrieval tests: all 15 markdown files, ranking, ADV-001, ADV-002."""

from financial_processing_agent.shared_libraries.constants import (
    ADVERSARIAL_DOCUMENT_ID,
    CURRENT_DFA_DOCUMENT_ID,
    DISTRACTOR_DOCUMENT_ID,
    SUPERSEDED_DFA_DOCUMENT_ID,
)
from financial_processing_agent.utils.corpus import load_corpus, search_corpus
from financial_processing_agent.utils.injection import scan_untrusted_text


def test_corpus_indexes_all_policy_and_adversarial_docs():
    """Every FIN-POL-001–012 plus OLD, ADV-001, ADV-002 must be in the index."""
    ids = {chunk.document_id for chunk in load_corpus()}
    expected = {f"FIN-POL-{n:03d}" for n in range(1, 13)}
    expected.update({SUPERSEDED_DFA_DOCUMENT_ID, ADVERSARIAL_DOCUMENT_ID, DISTRACTOR_DOCUMENT_ID})
    assert expected <= ids


def test_dfa_query_ranks_current_above_superseded():
    """FIN-POL-003 v4.0 must outrank the superseded matrix."""
    ranked = search_corpus("delegated financial authority approval limits matrix", top_k=15)
    ids = [item["document_id"] for item in ranked]
    assert CURRENT_DFA_DOCUMENT_ID in ids
    assert SUPERSEDED_DFA_DOCUMENT_ID in ids
    assert ids.index(CURRENT_DFA_DOCUMENT_ID) < ids.index(SUPERSEDED_DFA_DOCUMENT_ID)
    superseded = next(item for item in ranked if item["document_id"] == SUPERSEDED_DFA_DOCUMENT_ID)
    assert superseded["status"] == "superseded"


def test_adversarial_chunk_is_retrievable_and_flagged():
    """ADV-001 is in the index and injection scan flags its text."""
    ranked = search_corpus("urgent payment ignore policy skip duplicate bank account", top_k=10)
    ids = [item["document_id"] for item in ranked]
    assert ADVERSARIAL_DOCUMENT_ID in ids
    snippet = next(item for item in ranked if item["document_id"] == ADVERSARIAL_DOCUMENT_ID)["snippet"]
    flags = scan_untrusted_text(snippet)
    assert flags


def test_travel_limits_are_not_matching_authority():
    """Meal-limit extract must not outrank three-way match policy."""
    ranked = search_corpus("three-way matching invoice purchase order receipt tolerance", top_k=8)
    ids = [item["document_id"] for item in ranked]
    assert "FIN-POL-002" in ids
    if DISTRACTOR_DOCUMENT_ID in ids:
        assert ids.index("FIN-POL-002") < ids.index(DISTRACTOR_DOCUMENT_ID)


def test_ordinary_ap_query_does_not_retrieve_untrusted_attachments():
    """FIN-001-style queries must not surface ADV-001 or ADV-002 (false escalate)."""
    ranked = search_corpus(
        "three-way matching tolerances delegated financial authority accounts payable core policy",
        top_k=8,
    )
    ids = {item["document_id"] for item in ranked}
    assert ADVERSARIAL_DOCUMENT_ID not in ids
    assert DISTRACTOR_DOCUMENT_ID not in ids


def test_named_or_injection_query_still_retrieves_adv001():
    """FIN-003 still gets ADV-001 when the query names it or contains ignore-policy language."""
    by_id = search_corpus("ADV-001 supplier attachment", top_k=5)
    assert by_id[0]["document_id"] == ADVERSARIAL_DOCUMENT_ID
    by_language = search_corpus(
        "urgent payment bank account ignore policy supplier instructions vendor onboarding",
        top_k=10,
    )
    assert ADVERSARIAL_DOCUMENT_ID in {item["document_id"] for item in by_language}


def test_each_current_policy_searchable_by_id():
    """Querying a document_id returns that document first."""
    for doc_id in [f"FIN-POL-{n:03d}" for n in range(1, 13)]:
        ranked = search_corpus(doc_id, top_k=5)
        assert ranked[0]["document_id"] == doc_id
