"""Load mocked vendor/PO/history/cases JSON from the fixtures directory."""

from __future__ import annotations

import json
from pathlib import Path

from financial_processing_agent.shared_libraries.schemas import (
    InvoiceHistoryHit,
    PurchaseOrderRecord,
    VendorRecord,
)
from financial_processing_agent.shared_libraries.settings import settings


def _load(name: str) -> dict:
    """Read a JSON fixture file from settings.resolved_fixtures_dir."""
    path = settings.resolved_fixtures_dir / name
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_vendors() -> dict[str, VendorRecord]:
    """Vendor master keyed by vendor_id."""
    data = _load("vendors.json")
    return {item["vendor_id"]: VendorRecord.model_validate(item) for item in data}


def load_purchase_orders() -> dict[str, PurchaseOrderRecord]:
    """Purchase orders keyed by po_id (includes timeout and receipt flags)."""
    data = _load("purchase_orders.json")
    return {item["po_id"]: PurchaseOrderRecord.model_validate(item) for item in data}


def load_invoice_history() -> list[InvoiceHistoryHit]:
    """Paid/posted/held invoice fingerprints for duplicate checks."""
    data = _load("invoice_history.json")
    return [InvoiceHistoryHit.model_validate(item) for item in data]


def load_cases() -> dict[str, dict]:
    """FIN-00x evaluation cases keyed by case_id."""
    data = _load("cases.json")
    return {item["case_id"]: item for item in data}
