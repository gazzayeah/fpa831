"""Invoice fingerprint helpers for FIN-POL-005 duplicate detection."""

from __future__ import annotations

import re
from decimal import Decimal

from financial_processing_agent.shared_libraries.schemas import CaseRequest, InvoiceHistoryHit


def normalise_invoice_number(value: str) -> str:
    """Uppercase and strip punctuation so INV-500 and inv500 compare equal."""
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def find_duplicate_hits(
    case: CaseRequest, records: list[InvoiceHistoryHit]
) -> list[InvoiceHistoryHit]:
    """
    Exact match: same vendor, normalised invoice number, currency, gross amount.

    Fuzzy: same normalised number with a small amount variance, or same number
    without an exact amount match. Callers treat exact+PAID as REJECT_DUPLICATE.
    """
    needle = normalise_invoice_number(case.invoice_reference)
    hits: list[InvoiceHistoryHit] = []
    for record in records:
        if record.vendor_id != case.vendor_id or record.currency != case.currency:
            continue
        normalised = normalise_invoice_number(record.invoice_reference)
        amount_ok = record.amount == case.amount
        if normalised == needle and amount_ok:
            hits.append(record.model_copy(update={"match_type": "exact"}))
            continue
        if normalised == needle or (
            amount_ok is False
            and case.amount
            and abs(record.amount - case.amount) / case.amount < Decimal("0.005")
            and normalised == needle
        ):
            hits.append(record.model_copy(update={"match_type": "fuzzy"}))
        elif normalised == needle:
            hits.append(record.model_copy(update={"match_type": "fuzzy"}))
    return hits
