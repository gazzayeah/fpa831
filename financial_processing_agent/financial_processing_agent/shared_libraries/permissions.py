"""
Tool permission helpers.

Consequential tools are deny-by-default. ``workflow.Workflow`` calls
``before_tool`` which uses these predicates; do not invoke
``submit_finance_decision`` from the recommend LLM agent.
"""

from financial_processing_agent.shared_libraries.constants import (
    CONSEQUENTIAL_TOOLS,
    READ_ONLY_TOOLS,
)

ALLOWED_TOOLS = READ_ONLY_TOOLS | CONSEQUENTIAL_TOOLS


def is_consequential(tool_name: str) -> bool:
    """Return True if the tool records a posting/hold/reject (approval-gated)."""
    return tool_name in CONSEQUENTIAL_TOOLS


def is_allowed(tool_name: str) -> bool:
    """Return True if the tool is on the v1 allow-list."""
    return tool_name in ALLOWED_TOOLS
