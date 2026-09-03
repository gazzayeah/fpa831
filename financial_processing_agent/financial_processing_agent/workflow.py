"""
Coded control path used by CLI and eval (gather → reconcile → gate → approve).

This is the source of truth for FIN-001–005. The optional ADK ``SequentialAgent``
in ``agent.py`` exposes the same tools for interactive ``adk run`` but posting
is still gated here. Retrieved text is scanned for prompt injection; arithmetic
is never delegated to the model.
"""

from __future__ import annotations

import time
import uuid

from financial_processing_agent.callbacks.access import ToolDenied, before_tool
from financial_processing_agent.callbacks.observability import log_tool_event
from financial_processing_agent.callbacks.security import after_tool_security
from financial_processing_agent.shared_libraries.schemas import (
    CaseRequest,
    Citation,
    InvoiceHistoryHit,
    PurchaseOrderRecord,
    Recommendation,
    VendorRecord,
)
from financial_processing_agent.state.audit import AuditEvent
from financial_processing_agent.state.run_state import RunState
from financial_processing_agent.tools.check_invoice_history import check_invoice_history
from financial_processing_agent.tools.get_purchase_order import (
    PurchaseOrderTimeout,
    get_purchase_order,
)
from financial_processing_agent.tools.get_vendor_record import get_vendor_record
from financial_processing_agent.tools.reconcile_case import reconcile_case
from financial_processing_agent.tools.retrieve_finance_documents import retrieve_finance_documents
from financial_processing_agent.tools.submit_finance_decision import submit_finance_decision
from financial_processing_agent.utils.fixtures import load_cases
from financial_processing_agent.utils.injection import scan_untrusted_text
from financial_processing_agent.utils.run_store import RunStore


def _call(state: RunState, name: str, fn, *args, **kwargs):
    """
    Run an allow-listed tool with budget, timing, and audit logging.

    PurchaseOrderTimeout is logged as ``timeout`` then re-raised so
    ``Workflow._gather`` can record an unknown instead of failing the run.
    """
    before_tool(state, name)
    started = time.perf_counter()
    try:
        result = fn(*args, **kwargs)
    except PurchaseOrderTimeout:
        duration = (time.perf_counter() - started) * 1000
        state.tool_call_count += 1
        log_tool_event(state, name, "timeout", duration, {"po_id": kwargs.get("po_id", args[0] if args else "")})
        raise
    except Exception as exc:
        duration = (time.perf_counter() - started) * 1000
        state.tool_call_count += 1
        log_tool_event(state, name, "error", duration, {"error": type(exc).__name__})
        raise
    duration = (time.perf_counter() - started) * 1000
    state.tool_call_count += 1
    log_tool_event(state, name, "ok", duration, {})
    return result


class Workflow:
    """Persisted AP case runner. ``start`` stops at approval or a non-pay outcome."""

    def __init__(self, store: RunStore | None = None) -> None:
        """Bind a ``RunStore`` (defaults to settings.resolved_run_store_path)."""
        self.store = store or RunStore()

    def start(self, case: CaseRequest, retrieve_query: str | None = None) -> RunState:
        """
        Create a run, gather tools in sequence, reconcile, persist, return state.

        Stops at AWAITING_APPROVAL, HOLD, or REJECTED. Does not post.
        ``retrieve_query`` overrides the default RAG query (fixtures set this
        so FIN-003 retrieves ADV-001).
        """
        state = RunState(
            run_id=str(uuid.uuid4()),
            case_id=case.case_id,
            actor_id=case.actor_id,
            case=case,
        )
        state.audit.append(
            AuditEvent(run_id=state.run_id, event_type="run_start", detail={"case_id": case.case_id})
        )
        try:
            self._gather(state, retrieve_query=retrieve_query)
            self._reconcile(state)
        except Exception as exc:
            state.status = "FAILED"
            state.last_error = str(exc)
            self.store.save(state)
            raise
        self.store.save(state)
        return state

    def start_fixture(self, case_id: str) -> RunState:
        """Start from ``fixtures/cases.json`` (FIN-001–005)."""
        raw = load_cases()[case_id]
        case = CaseRequest.model_validate(raw)
        return self.start(case, retrieve_query=raw.get("retrieve_query"))

    def get(self, run_id: str) -> RunState | None:
        """Return persisted run state or None."""
        return self.store.get(run_id)

    def approve(self, run_id: str, actor_id: str, idempotency_key: str) -> RunState:
        """
        Human approval gate, then a single sandbox submit.

        If the run is already SUBMITTED with the same idempotency_key, return
        the existing posting (FIN-005 replay). Otherwise status must be
        AWAITING_APPROVAL (or already APPROVED) before submit is allowed.
        """
        state = self._require(run_id)
        if (
            state.status == "SUBMITTED"
            and state.approval.idempotency_key == idempotency_key
        ):
            state.audit.append(
                AuditEvent(
                    run_id=state.run_id,
                    event_type="approval_replay",
                    outcome="ok",
                    detail={"idempotency_key": idempotency_key},
                )
            )
            self.store.save(state)
            return state
        if state.status not in {"AWAITING_APPROVAL", "APPROVED"}:
            raise ToolDenied(f"run {run_id} is not awaiting approval (status={state.status})")
        from datetime import datetime, timezone

        state.approval.decision = "approved"
        state.approval.actor_id = actor_id
        state.approval.timestamp = datetime.now(timezone.utc).isoformat()
        state.approval.idempotency_key = idempotency_key
        state.status = "APPROVED"
        posted = _call(
            state,
            "submit_finance_decision",
            submit_finance_decision,
            state.run_id,
            state.recommendation.outcome if state.recommendation else "APPROVE_FOR_POSTING",
            idempotency_key,
            True,
        )
        state.posting_reference = posted["posting_reference"]
        state.status = "SUBMITTED"
        if state.recommendation:
            action = "submit_replay" if posted.get("replay") else "submit_once"
            if action not in state.recommendation.actions_taken:
                state.recommendation.actions_taken.append(action)
        state.previous_decisions.append(posted)
        self.store.save(state)
        return state

    def reject(self, run_id: str, actor_id: str) -> RunState:
        """Human rejection: no posting tool is called."""
        state = self._require(run_id)
        state.status = "REJECTED_BY_HUMAN"
        state.approval.decision = "rejected"
        state.approval.actor_id = actor_id
        self.store.save(state)
        return state

    def _require(self, run_id: str) -> RunState:
        """Load a run or raise KeyError."""
        state = self.store.get(run_id)
        if state is None:
            raise KeyError(run_id)
        return state

    def _gather(self, state: RunState, retrieve_query: str | None) -> None:
        """Read-only tools: RAG, vendor, history, PO (timeout recorded as unknown)."""
        state.status = "GATHERING"
        query = retrieve_query or " ".join(
            [
                state.case.notes,
                "accounts payable invoice purchase order receipt vendor policy",
            ]
        )
        retrieved = _call(state, "retrieve_finance_documents", retrieve_finance_documents, query)
        state.citations = [Citation.model_validate(item) for item in retrieved["chunks"]]
        blob = state.case.notes + "\n" + "\n".join(c.snippet for c in state.citations)
        state.injection_flags = after_tool_security(
            "retrieve_finance_documents",
            blob,
            scan_untrusted_text(state.case.notes),
        )

        vendor = _call(state, "get_vendor_record", get_vendor_record, state.case.vendor_id)
        if vendor.get("found"):
            state.vendor = VendorRecord.model_validate(vendor)

        history = _call(
            state,
            "check_invoice_history",
            check_invoice_history,
            state.case.vendor_id,
            state.case.invoice_reference,
            str(state.case.amount),
            state.case.currency,
        )
        state.invoice_history = [InvoiceHistoryHit.model_validate(item) for item in history["hits"]]

        po_id = state.case.po_id
        if po_id:
            try:
                po = _call(state, "get_purchase_order", get_purchase_order, po_id)
                if po.get("found"):
                    state.purchase_order = PurchaseOrderRecord.model_validate(
                        {k: v for k, v in po.items() if k != "found"}
                    )
            except PurchaseOrderTimeout:
                state.unknowns.append("purchase_order_timeout")

    def _reconcile(self, state: RunState) -> None:
        """Deterministic match/duplicate/policy outcome; sets AWAITING_APPROVAL or HOLD/REJECTED."""
        state.status = "RECONCILING"
        po_timeout = "purchase_order_timeout" in state.unknowns
        vendor_payload = state.vendor.model_dump() if state.vendor else None
        po_payload = None
        if state.purchase_order:
            po_payload = state.purchase_order.model_dump(mode="json")
            po_payload["found"] = True
        rec = _call(
            state,
            "reconcile_case",
            reconcile_case,
            state.case.model_dump(mode="json"),
            vendor_payload,
            po_payload,
            [h.model_dump(mode="json") for h in state.invoice_history],
            state.injection_flags,
            po_timeout,
        )
        recommendation = Recommendation.model_validate(rec)
        recommendation.citations = state.citations
        state.recommendation = recommendation
        state.exceptions = recommendation.exceptions
        state.unknowns = list(dict.fromkeys([*state.unknowns, *recommendation.unknowns]))
        if recommendation.outcome == "APPROVE_FOR_POSTING":
            state.status = "AWAITING_APPROVAL"
        elif recommendation.outcome == "REJECT_DUPLICATE":
            state.status = "REJECTED"
        else:
            state.status = "HOLD"
