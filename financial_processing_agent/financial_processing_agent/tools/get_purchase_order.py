"""Mock purchase-order + goods-receipt tool. FIN-004 injects a timeout via the fixture."""

from __future__ import annotations

from financial_processing_agent.utils.fixtures import load_purchase_orders


class PurchaseOrderTimeout(TimeoutError):
    """Legacy alias. Timeouts are returned as ``timeout=True`` so ADK does not abort."""


def get_purchase_order(po_id: str) -> dict:
    """
    Return lines, currency, approval status, receipts.

    When the fixture sets ``timeout: true`` (FIN-004 / PO-4001), return
    ``found=False, timeout=True`` instead of raising. ADK treats a raised
    exception as a crashed turn; the coded Workflow treats ``timeout=True``
    as an unknown and holds.
    """
    orders = load_purchase_orders()
    record = orders.get(po_id)
    if record is None:
        return {"found": False, "po_id": po_id, "timeout": False}
    if record.timeout:
        return {
            "found": False,
            "po_id": po_id,
            "timeout": True,
            "error": f"get_purchase_order timed out for {po_id}",
        }
    payload = record.model_dump(mode="json")
    payload["found"] = True
    payload["timeout"] = False
    return payload
