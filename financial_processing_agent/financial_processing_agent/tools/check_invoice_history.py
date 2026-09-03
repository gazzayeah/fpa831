"""Duplicate detection against mocked paid/posted/held invoice history."""

from __future__ import annotations

from decimal import Decimal

from financial_processing_agent.shared_libraries.schemas import CaseRequest
from financial_processing_agent.utils.duplicates import find_duplicate_hits
from financial_processing_agent.utils.fixtures import load_invoice_history


def check_invoice_history(
    vendor_id: str,
    invoice_reference: str,
    amount: str,
    currency: str = "AUD",
) -> dict:
    """
    Compare this invoice against mocked paid/posted/held history.

    Amount is a string so ADK can pass JSON numbers without float drift;
    it is converted to Decimal inside the tool.

    Returns:
        ``{"hits": [...]}`` each with record_id and match_type exact|fuzzy.
    """
    case = CaseRequest(
        case_id="lookup",
        invoice_reference=invoice_reference,
        vendor_id=vendor_id,
        amount=Decimal(amount),
        currency=currency,
    )
    hits = find_duplicate_hits(case, load_invoice_history())
    return {"hits": [hit.model_dump(mode="json") for hit in hits]}
