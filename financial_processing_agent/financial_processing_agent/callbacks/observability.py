"""Audit logging with PII/bank redaction. Safe to call after every tool."""

from __future__ import annotations

from financial_processing_agent.state.audit import AuditEvent
from financial_processing_agent.state.run_state import RunState
from financial_processing_agent.utils.masking import redact_log_detail


def log_tool_event(
    state: RunState,
    tool_name: str,
    outcome: str,
    duration_ms: float,
    detail: dict | None = None,
) -> None:
    """Append a timestamped tool event. ``detail`` is redacted before storage."""
    event = AuditEvent(
        run_id=state.run_id,
        event_type=f"tool:{tool_name}",
        outcome=outcome,
        duration_ms=duration_ms,
        detail=redact_log_detail(detail or {}),
    )
    state.audit.append(event)
