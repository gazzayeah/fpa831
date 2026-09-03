"""Mock vendor-master tool (status, masked payment, risk flags, last-updated)."""

from __future__ import annotations

from financial_processing_agent.utils.fixtures import load_vendors


def get_vendor_record(vendor_id: str) -> dict:
    """
    Look up a vendor fixture by id.

    Returns a VendorRecord dict plus ``found=True``, or ``found=False`` if
    unknown. Payment details are already last4-only in the fixture.
    """
    vendors = load_vendors()
    record = vendors.get(vendor_id)
    if record is None:
        return {"found": False, "vendor_id": vendor_id}
    payload = record.model_dump()
    payload["found"] = True
    return payload
