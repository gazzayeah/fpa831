"""
Sandbox posting API. Not connected to a real bank or ERP.

Requires ``approved=True`` and an idempotency key. Repeating the key returns
the same posting_reference (FIN-005).
"""

from __future__ import annotations

from datetime import datetime, timezone


# In-memory sandbox ledger keyed by idempotency_key. Not durable across processes.
# ``reset_postings`` clears this between eval runs so FIN-001 and FIN-005 do not collide.
_POSTINGS: dict[str, dict] = {}


def submit_finance_decision(
    run_id: str,
    outcome: str,
    idempotency_key: str,
    approved: bool,
) -> dict:
    """
    Record one sandbox decision and return a posting reference.

    Args:
        run_id: Workflow run that owns this posting.
        outcome: Recommendation outcome being recorded (e.g. APPROVE_FOR_POSTING).
        idempotency_key: Caller-supplied key. The same key always returns the
            same ``posting_reference`` with ``replay=True`` (FIN-005).
        approved: Must be True. The workflow only passes True after human approval;
            this flag is a second belt-and-braces check inside the tool.

    Returns:
        Dict with posting_reference, outcome, idempotency_key, submitted_at, replay.

    Raises:
        PermissionError: ``approved`` is False.
        ValueError: ``idempotency_key`` is empty.
    """
    if not approved:
        raise PermissionError("submit_finance_decision denied: not approved")
    if not idempotency_key:
        raise ValueError("idempotency_key is required")
    existing = _POSTINGS.get(idempotency_key)
    if existing:
        replay = dict(existing)
        replay["replay"] = True
        return replay
    posting = {
        "posting_reference": f"POST-{run_id}",
        "outcome": outcome,
        "idempotency_key": idempotency_key,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "replay": False,
    }
    _POSTINGS[idempotency_key] = posting
    return posting


def reset_postings() -> None:
    """Clear in-memory postings between eval runs."""
    _POSTINGS.clear()
