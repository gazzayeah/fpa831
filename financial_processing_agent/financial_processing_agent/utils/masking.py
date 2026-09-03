"""Log redaction. FIN-POL-010: never write full bank numbers or secrets to general logs."""

from __future__ import annotations

from typing import Any


def mask_bank(value: str) -> str:
    """Keep last four digits only (FIN-POL-004 logging rule)."""
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) < 4:
        return "****"
    return f"****{digits[-4:]}"


_SENSITIVE_KEYS = {"account", "bank", "iban", "password", "secret", "tax_id"}


def redact_log_detail(detail: dict[str, Any]) -> dict[str, Any]:
    """Shallow-copy a log dict, masking keys whose names look like secrets or bank data."""
    redacted: dict[str, Any] = {}
    for key, value in detail.items():
        lowered = key.lower()
        if any(token in lowered for token in _SENSITIVE_KEYS):
            redacted[key] = mask_bank(str(value))
        elif isinstance(value, dict):
            redacted[key] = redact_log_detail(value)
        else:
            redacted[key] = value
    return redacted
