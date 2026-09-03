"""
Domain constants shared by tools, matching, and eval.

These are Northstar AP policy codes and tool names, not environment config.
Keep GCP project IDs and model names in ``settings.py``.
"""

# FIN-POL-001 processing outcomes. A recommendation is not an approval.
OUTCOMES = (
    "APPROVE_FOR_POSTING",
    "HOLD_FOR_INFORMATION",
    "REJECT_DUPLICATE",
    "REJECT_INVALID",
    "ESCALATE_CONTROL_REVIEW",
)

# FIN-POL-007 primary exception categories (one per failed control).
EXCEPTION_CATEGORIES = (
    "MISSING_PO",
    "MISSING_RECEIPT",
    "PRICE_VARIANCE",
    "QUANTITY_VARIANCE",
    "DUPLICATE_RISK",
    "VENDOR_BLOCK",
    "BANK_CHANGE",
    "AUTHORITY_GAP",
    "TAX_QUERY",
    "OTHER_CONTROL_RISK",
)

# Only this tool may post/hold/reject money-adjacent outcomes, and only after approval.
CONSEQUENTIAL_TOOLS = frozenset({"submit_finance_decision"})

READ_ONLY_TOOLS = frozenset(
    {
        "retrieve_finance_documents",
        "get_vendor_record",
        "get_purchase_order",
        "check_invoice_history",
        "reconcile_case",
    }
)

# FIN-POL-004: invoices for these vendor statuses must be held.
BLOCKED_VENDOR_STATUSES = frozenset(
    {"BLOCKED", "DORMANT", "SANCTIONS_REVIEW", "PENDING_VERIFICATION"}
)

# Corpus document_ids used in retrieval tests and FIN-003.
CURRENT_DFA_DOCUMENT_ID = "FIN-POL-003"
SUPERSEDED_DFA_DOCUMENT_ID = "FIN-POL-003-OLD"
ADVERSARIAL_DOCUMENT_ID = "ADV-001"
DISTRACTOR_DOCUMENT_ID = "ADV-002"
