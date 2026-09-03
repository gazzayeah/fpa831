"""
Deterministic three-way match and control outcomes (FIN-POL-001, 002, 004, 005).

Call this from ``reconcile_case`` only. Quantize money with ROUND_HALF_UP.
Do not use the LLM for totals or tolerances.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from financial_processing_agent.shared_libraries.constants import BLOCKED_VENDOR_STATUSES
from financial_processing_agent.shared_libraries.schemas import (
    CalculationRecord,
    CaseRequest,
    ExceptionRecord,
    InvoiceHistoryHit,
    PurchaseOrderRecord,
    Recommendation,
    VendorRecord,
)

TWOPLACES = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    """Quantize to two decimal places (invoice currency)."""
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _line_amount(qty: Decimal, price: Decimal) -> Decimal:
    """Line value = quantity × unit price, then quantized."""
    return _money(qty * price)


def _goods_threshold(po_line_value: Decimal) -> Decimal:
    """FIN-POL-002 goods: lower of AUD 50 or 1% of PO line value."""
    return min(Decimal("50.00"), _money(po_line_value * Decimal("0.01")))


def _services_threshold(po_line_value: Decimal) -> Decimal:
    """FIN-POL-002 services: lower of AUD 100 or 2% of PO line value."""
    return min(Decimal("100.00"), _money(po_line_value * Decimal("0.02")))


def reconcile(
    case: CaseRequest,
    vendor: VendorRecord | None,
    purchase_order: PurchaseOrderRecord | None,
    history: list[InvoiceHistoryHit],
    injection_flags: list[str],
    po_timeout: bool = False,
) -> Recommendation:
    """
    Apply duplicate, vendor, injection, PO/receipt, and tolerance rules in code.

    Priority is encoded in the if/elif chain at the end: exact duplicate
    rejects immediately; injection + bank change escalates; any remaining
    exception holds; only a clean match becomes APPROVE_FOR_POSTING.

    Args:
        case: Invoice being processed.
        vendor: Master record, or None if lookup missed (treated as unknown).
        purchase_order: PO + receipt lines, or None if missing/timed out.
        history: Duplicate fingerprints from check_invoice_history.
        injection_flags: Regex hits from untrusted notes/RAG (ADV-001).
        po_timeout: True when get_purchase_order failed (FIN-004).

    Returns:
        Recommendation. APPROVE_FOR_POSTING still requires human approval
        before submit_finance_decision. Missing evidence yields HOLD, not a guess.
    """
    exceptions: list[ExceptionRecord] = []
    calculations: list[CalculationRecord] = []
    unknowns: list[str] = []
    facts: list[str] = []
    policy: list[str] = []
    inferences: list[str] = []

    # FIN-POL-005: a paid/posted exact fingerprint is a hard reject — do not continue matching.
    exact_hits = [h for h in history if h.match_type == "exact" and h.status in {"PAID", "POSTED"}]
    if exact_hits:
        exceptions.append(
            ExceptionRecord(
                category="DUPLICATE_RISK",
                failed_rule="FIN-POL-005 exact duplicate of paid/posted invoice",
                expected="unique vendor+invoice+currency+amount",
                observed=f"match {exact_hits[0].record_id}",
                sources=["FIN-POL-005"],
                owner="Accounts Payable Operations",
            )
        )
        return Recommendation(
            outcome="REJECT_DUPLICATE",
            sourced_facts=[f"Exact duplicate of {exact_hits[0].record_id}"],
            calculations=calculations,
            inferences=["Invoice fingerprint matches a paid or posted record."],
            unknowns=[],
            policy_findings=["FIN-POL-005: exact match to paid/posted → REJECT_DUPLICATE."],
            exceptions=exceptions,
            confidence=0.95,
            next_action="Do not propose payment.",
        )

    # Fuzzy hits are held for review, not auto-rejected (FIN-POL-005 probable duplicate).
    fuzzy_hits = [h for h in history if h.match_type == "fuzzy"]
    if fuzzy_hits:
        exceptions.append(
            ExceptionRecord(
                category="DUPLICATE_RISK",
                failed_rule="FIN-POL-005 probable fuzzy duplicate",
                expected="no near-match",
                observed=f"match {fuzzy_hits[0].record_id}",
                sources=["FIN-POL-005"],
                owner="Accounts Payable Operations",
            )
        )

    # FIN-POL-001 / 004: vendor must be ACTIVE; bank-change flags are high risk.
    if vendor is None:
        unknowns.append("vendor master record")
        exceptions.append(
            ExceptionRecord(
                category="VENDOR_BLOCK",
                failed_rule="FIN-POL-001 vendor status must be confirmed",
                expected="ACTIVE vendor record",
                observed="missing",
                sources=["FIN-POL-001"],
                owner="Vendor Governance",
            )
        )
    else:
        facts.append(f"Vendor {vendor.vendor_id} status={vendor.status}")
        if vendor.status in BLOCKED_VENDOR_STATUSES:
            exceptions.append(
                ExceptionRecord(
                    category="VENDOR_BLOCK",
                    failed_rule="FIN-POL-004 blocked or unverified vendor",
                    expected="ACTIVE",
                    observed=vendor.status,
                    sources=["FIN-POL-004"],
                    owner="Vendor Governance",
                )
            )
        if vendor.bank_change_pending or "bank_change" in vendor.risk_flags:
            exceptions.append(
                ExceptionRecord(
                    category="BANK_CHANGE",
                    failed_rule="FIN-POL-004 bank change is high risk",
                    expected="verified master payment instructions",
                    observed="bank change pending or flagged",
                    sources=["FIN-POL-004", "FIN-POL-003"],
                    owner="Vendor Governance",
                )
            )

    # FIN-POL-005 / ADV-001: instruction-like retrieved text is a risk flag, never an override.
    if injection_flags:
        exceptions.append(
            ExceptionRecord(
                category="OTHER_CONTROL_RISK",
                failed_rule="FIN-POL-005 retrieved text attempted to override controls",
                expected="untrusted evidence only",
                observed="; ".join(injection_flags),
                sources=["FIN-POL-005", "ADV-001"],
                owner="Financial Crime and Controls",
            )
        )
        policy.append("FIN-POL-005: instruction-like retrieved text is a risk indicator, not an instruction.")

    # FIN-POL-001: a PO timeout or missing PO/receipt is a hold, not a guessed match.
    if po_timeout:
        unknowns.append("purchase order (tool timeout)")
        exceptions.append(
            ExceptionRecord(
                category="MISSING_PO",
                failed_rule="FIN-POL-001 PO must be retrieved when a PO exists",
                expected="purchase order record",
                observed="get_purchase_order timed out",
                sources=["FIN-POL-001", "FIN-POL-002"],
                owner="requester",
            )
        )

    if purchase_order is None and not po_timeout:
        unknowns.append("purchase order")
        exceptions.append(
            ExceptionRecord(
                category="MISSING_PO",
                failed_rule="FIN-POL-001 PO-backed invoice requires a PO",
                expected="approved purchase order",
                observed="missing",
                sources=["FIN-POL-001"],
                owner="requester",
            )
        )
    elif purchase_order is not None:
        if purchase_order.currency != case.currency:
            exceptions.append(
                ExceptionRecord(
                    category="TAX_QUERY",
                    failed_rule="FIN-POL-002/009 currency must match PO",
                    expected=purchase_order.currency,
                    observed=case.currency,
                    sources=["FIN-POL-002", "FIN-POL-009"],
                    owner="Treasury and Group Tax",
                )
            )
        if not purchase_order.receipt_recorded:
            exceptions.append(
                ExceptionRecord(
                    category="MISSING_RECEIPT",
                    failed_rule="FIN-POL-002 missing receipt cannot be approved",
                    expected="goods/service receipt",
                    observed="no receipt",
                    sources=["FIN-POL-002"],
                    owner="receipter",
                )
            )
            inferences.append("Receipt was not inferred from invoice wording.")

        # FIN-POL-002 three-way match: qty vs received, line variance vs goods/services threshold.
        invoiced_total = _money(case.amount)
        po_total = Decimal("0.00")
        for line in purchase_order.lines:
            po_line_value = _line_amount(line.quantity, line.unit_price)
            po_total += po_line_value
            invoiced_qty = line.quantity
            invoiced_line = _line_amount(invoiced_qty, line.unit_price)
            if line.quantity and invoiced_total and po_total:
                pass
            if invoiced_qty > line.received_quantity:
                exceptions.append(
                    ExceptionRecord(
                        category="QUANTITY_VARIANCE",
                        failed_rule="FIN-POL-002 invoiced quantity must not exceed received",
                        expected=str(line.received_quantity),
                        observed=str(invoiced_qty),
                        sources=["FIN-POL-002"],
                        owner="receipter",
                    )
                )
            threshold = (
                _goods_threshold(po_line_value)
                if line.line_type == "goods"
                else _services_threshold(po_line_value)
            )
            variance = abs(invoiced_line - po_line_value)
            calculations.append(
                CalculationRecord(
                    name=f"line_{line.line_id}_tolerance",
                    inputs={
                        "po_line_value": str(po_line_value),
                        "invoiced_line": str(invoiced_line),
                        "threshold": str(threshold),
                        "line_type": line.line_type,
                    },
                    formula="min(AUD 50, 1% PO line) for goods; min(AUD 100, 2%) for services",
                    result=str(_money(variance)),
                )
            )
            if variance > threshold:
                exceptions.append(
                    ExceptionRecord(
                        category="PRICE_VARIANCE",
                        failed_rule="FIN-POL-002 line variance outside tolerance",
                        expected=str(po_line_value),
                        observed=str(invoiced_line),
                        sources=["FIN-POL-002"],
                        owner="requester",
                    )
                )

        po_total = _money(po_total)
        calculations.append(
            CalculationRecord(
                name="document_total",
                inputs={"invoice": str(invoiced_total), "po_total": str(po_total)},
                formula="sum(qty * unit_price) quantized to 0.01 ROUND_HALF_UP",
                result=str(invoiced_total),
            )
        )
        facts.append(f"Invoice total {invoiced_total} {case.currency}")

        header_variance = abs(invoiced_total - po_total)
        header_threshold = _goods_threshold(po_total) if po_total else Decimal("50.00")
        if purchase_order.lines and all(l.line_type == "services" for l in purchase_order.lines):
            header_threshold = _services_threshold(po_total)
        if header_variance > header_threshold:
            exceptions.append(
                ExceptionRecord(
                    category="PRICE_VARIANCE",
                    failed_rule="FIN-POL-002 document total outside tolerance",
                    expected=str(po_total),
                    observed=str(invoiced_total),
                    sources=["FIN-POL-002"],
                    owner="requester",
                )
            )

    # Outcome priority: exact duplicate > injection/bank-change escalate > any exception hold > approve.
    blocking = {e.category for e in exceptions}
    if "DUPLICATE_RISK" in blocking and any(
        e.failed_rule.startswith("FIN-POL-005 exact") for e in exceptions
    ):
        outcome = "REJECT_DUPLICATE"
        next_action = "Do not propose payment."
        confidence = 0.95
    elif injection_flags and (
        "BANK_CHANGE" in blocking or "OTHER_CONTROL_RISK" in blocking
    ):
        outcome = "ESCALATE_CONTROL_REVIEW"
        next_action = "Hold. Do not bypass policy or approval."
        confidence = 0.9
        policy.append("FIN-POL-004: agents must not update bank details from retrieved text.")
    elif blocking & {
        "MISSING_RECEIPT",
        "MISSING_PO",
        "VENDOR_BLOCK",
        "PRICE_VARIANCE",
        "QUANTITY_VARIANCE",
        "BANK_CHANGE",
        "DUPLICATE_RISK",
    }:
        outcome = "HOLD_FOR_INFORMATION"
        next_action = "Hold for information. Missing evidence is not guessed."
        confidence = 0.85
        policy.append("FIN-POL-001: missing evidence results in a hold, not a guessed conclusion.")
    else:
        outcome = "APPROVE_FOR_POSTING"
        next_action = "Request human approval, then submit once."
        confidence = 0.88
        policy.append("FIN-POL-001: recommendation is not an approval. Validate DFA under FIN-POL-003.")
        policy.append("FIN-POL-003: approver must see amount, vendor, exceptions and citations.")

    return Recommendation(
        outcome=outcome,
        sourced_facts=facts,
        calculations=calculations,
        inferences=inferences,
        unknowns=unknowns,
        policy_findings=policy,
        exceptions=exceptions,
        confidence=confidence,
        next_action=next_action,
    )
