"""Constrained calculation tool wrapping ``utils.matching.reconcile`` (not model arithmetic)."""

from __future__ import annotations

from financial_processing_agent.shared_libraries.schemas import (
    CaseRequest,
    InvoiceHistoryHit,
    PurchaseOrderRecord,
    VendorRecord,
)
from financial_processing_agent.utils.matching import reconcile


def reconcile_case(
    case: dict,
    vendor: dict | None,
    purchase_order: dict | None,
    history: list[dict],
    injection_flags: list[str],
    po_timeout: bool = False,
) -> dict:
    """
    Tool wrapper around ``utils.matching.reconcile``.

    Accepts JSON-friendly dicts (ADK tool arguments) and returns a
    ``Recommendation`` dict. Arithmetic lives in ``matching.reconcile``, not here.

    Args:
        case: CaseRequest fields (case_id, invoice_reference, vendor_id, amount, …).
        vendor: VendorRecord dict, or None if the master lookup missed.
        purchase_order: PurchaseOrderRecord dict with ``found=True``, or None.
        history: InvoiceHistoryHit dicts from ``check_invoice_history``.
        injection_flags: Patterns matched in untrusted notes/RAG snippets.
        po_timeout: True when ``get_purchase_order`` timed out (FIN-004).
    """
    recommendation = reconcile(
        case=CaseRequest.model_validate(case),
        vendor=VendorRecord.model_validate(vendor) if vendor and vendor.get("found", True) and "vendor_id" in (vendor or {}) else None,
        purchase_order=PurchaseOrderRecord.model_validate(
            {k: v for k, v in (purchase_order or {}).items() if k != "found"}
        )
        if purchase_order and purchase_order.get("found")
        else None,
        history=[InvoiceHistoryHit.model_validate(item) for item in history],
        injection_flags=injection_flags,
        po_timeout=po_timeout,
    )
    return recommendation.model_dump(mode="json")
