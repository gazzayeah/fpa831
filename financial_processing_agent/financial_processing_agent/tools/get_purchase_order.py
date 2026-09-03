"""Mock purchase-order + goods-receipt tool. FIN-004 injects a timeout via the fixture."""

from __future__ import annotations

from financial_processing_agent.utils.fixtures import load_purchase_orders


class PurchaseOrderTimeout(TimeoutError):
    """Simulated PO API timeout (bounded retry/fail is handled by Workflow)."""


def get_purchase_order(po_id: str) -> dict:
    """
    Return lines, currency, approval status, receipts.

    Raises PurchaseOrderTimeout when the fixture sets ``timeout: true``.
    """
    orders = load_purchase_orders()
    record = orders.get(po_id)
    if record is None:
        return {"found": False, "po_id": po_id, "timeout": False}
    if record.timeout:
        raise PurchaseOrderTimeout(f"get_purchase_order timed out for {po_id}")
    payload = record.model_dump(mode="json")
    payload["found"] = True
    return payload
