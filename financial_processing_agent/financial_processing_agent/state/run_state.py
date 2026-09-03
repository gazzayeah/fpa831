"""
Short-term run memory persisted to SQLite and returned by get-run.

Identity is ``run_id`` / ``case_id`` / ``actor_id`` (processor), not a chat
user_id. Retrieval scores live on ``citations``, not as a loose memory field.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from financial_processing_agent.shared_libraries.schemas import (
    CaseRequest,
    Citation,
    ExceptionRecord,
    InvoiceHistoryHit,
    PurchaseOrderRecord,
    Recommendation,
    VendorRecord,
)
from financial_processing_agent.state.audit import AuditEvent


class ApprovalRecord(BaseModel):
    """Human decision plus idempotency key (FIN-005: replay must not double-post)."""

    decision: str = ""
    actor_id: str = ""
    timestamp: str = ""
    idempotency_key: str = ""


class RunState(BaseModel):
    """
    Full workflow snapshot persisted after every stage.

    Status typically moves GATHERING → RECONCILING → AWAITING_APPROVAL | HOLD |
    REJECTED, then APPROVED → SUBMITTED after a human decision. FAILED is set
    if a tool raises unexpectedly.
    """

    run_id: str
    case_id: str
    actor_id: str = "ap-processor"  # processor identity, not a chat user_id
    status: str = "GATHERING"
    case: CaseRequest
    vendor: VendorRecord | None = None
    purchase_order: PurchaseOrderRecord | None = None
    invoice_history: list[InvoiceHistoryHit] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)  # ranking scores live here
    exceptions: list[ExceptionRecord] = Field(default_factory=list)
    recommendation: Recommendation | None = None
    unknowns: list[str] = Field(default_factory=list)
    approval: ApprovalRecord = Field(default_factory=ApprovalRecord)
    previous_decisions: list[dict[str, Any]] = Field(default_factory=list)
    posting_reference: str | None = None  # set only after a successful sandbox submit
    step_count: int = 0
    tool_call_count: int = 0  # compared to the budget in callbacks.access
    last_error: str = ""
    injection_flags: list[str] = Field(default_factory=list)
    audit: list[AuditEvent] = Field(default_factory=list)
