"""Append-only audit events attached to ``RunState.audit``. Do not log bank details."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    """One tool/run event: timestamp, correlation id, outcome, duration, redacted detail."""

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    run_id: str
    event_type: str
    outcome: str = "ok"
    duration_ms: float | None = None
    detail: dict[str, Any] = Field(default_factory=dict)
