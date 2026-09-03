"""
Pydantic contracts for cases, tools, and the typed recommendation.

The brief requires the final result to separate sourced facts, calculations,
inferences, unknowns, policy findings, and actions. ``Recommendation`` is that
shape. Money fields use ``Decimal`` — never float.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class CaseRequest(BaseModel):
    """Inbound invoice-processing request (start-run payload). Notes are untrusted."""

    case_id: str
    invoice_reference: str
    vendor_id: str
    amount: Decimal
    currency: str = "AUD"
    notes: str = ""
    attachments: list[str] = Field(default_factory=list)
    actor_id: str = "ap-processor"
    po_id: str = ""


class Citation(BaseModel):
    """One RAG hit. ``relevance`` is retriever-assigned; the model must not invent it."""

    document_id: str
    document_type: str = "policy"
    version: str = ""
    page: str = ""
    relevance: float = 0.0
    status: str = "current"
    snippet: str = ""
    title: str = ""


class ExceptionRecord(BaseModel):
    """FIN-POL-007 exception: failed rule, expected vs observed, cited sources, owner."""

    category: str
    failed_rule: str
    expected: str
    observed: str
    sources: list[str] = Field(default_factory=list)
    owner: str = ""


class CalculationRecord(BaseModel):
    """Authoritative arithmetic trail (FIN-POL-002: model math is not authoritative)."""

    name: str
    inputs: dict[str, Any]
    formula: str
    result: str
    rounding: str = "ROUND_HALF_UP"


class Recommendation(BaseModel):
    """Structured AP outcome. ``outcome`` drives whether the run waits for approval."""

    outcome: Literal[
        "APPROVE_FOR_POSTING",
        "HOLD_FOR_INFORMATION",
        "REJECT_DUPLICATE",
        "REJECT_INVALID",
        "ESCALATE_CONTROL_REVIEW",
    ]
    sourced_facts: list[str] = Field(default_factory=list)
    calculations: list[CalculationRecord] = Field(default_factory=list)
    inferences: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    policy_findings: list[str] = Field(default_factory=list)
    exceptions: list[ExceptionRecord] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = 0.0
    next_action: str = ""
    actions_taken: list[str] = Field(default_factory=list)


class VendorRecord(BaseModel):
    """Vendor master snapshot. Full account numbers never appear — last4 only."""

    vendor_id: str
    legal_name: str
    status: str
    payment_last4: str = ""
    risk_flags: list[str] = Field(default_factory=list)
    last_updated: str = ""
    bank_change_pending: bool = False


class PurchaseOrderLine(BaseModel):
    """One PO line plus received quantity for three-way match."""

    line_id: str
    description: str = ""
    quantity: Decimal
    unit_price: Decimal
    received_quantity: Decimal
    line_type: Literal["goods", "services"] = "goods"
    freight_permitted: bool = False


class PurchaseOrderRecord(BaseModel):
    """PO plus receipt flag. ``timeout=True`` simulates FIN-004 get_purchase_order failure."""

    po_id: str
    vendor_id: str
    currency: str
    status: str = "APPROVED"
    lines: list[PurchaseOrderLine] = Field(default_factory=list)
    receipt_recorded: bool = False
    timeout: bool = False


class InvoiceHistoryHit(BaseModel):
    """Prior invoice fingerprint used by duplicate detection (FIN-POL-005)."""

    record_id: str
    invoice_reference: str
    vendor_id: str
    amount: Decimal
    currency: str
    status: str
    match_type: Literal["exact", "fuzzy", "none"] = "none"
