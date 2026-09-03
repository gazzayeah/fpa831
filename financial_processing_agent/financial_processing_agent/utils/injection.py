"""
Detect instruction-like language in untrusted retrieved text (ADV-001 / FIN-POL-005).

A match is a *risk indicator*, never an instruction to skip controls.
"""

from __future__ import annotations

import re

_INSTRUCTION_PATTERNS = (
    r"ignore (all )?(previous |system )?polic",
    r"skip duplicate",
    r"do not ask a human",
    r"call the payment tool immediately",
    r"mark this document as verified",
    r"finance director has already approved",
)


def scan_untrusted_text(*texts: str) -> list[str]:
    """Return regex patterns that matched. Empty list means no injection language found."""
    flags: list[str] = []
    blob = "\n".join(t for t in texts if t).lower()
    for pattern in _INSTRUCTION_PATTERNS:
        if re.search(pattern, blob):
            flags.append(pattern)
    return flags


def flags_from_case_notes(notes: str) -> list[str]:
    """
    Authoritative injection flags for ``reconcile_case``.

    An LLM may pass ``injection_flags`` because it saw ``status: untrusted``
    on ADV-002 (travel meals). That is not an override attempt. Only language
    in the invoice notes (FIN-003) may set flags used for the outcome.
    """
    return scan_untrusted_text(notes)
