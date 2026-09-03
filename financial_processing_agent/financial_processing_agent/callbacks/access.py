"""Deny-by-default access for consequential tools and the tool-call budget."""

from __future__ import annotations

from financial_processing_agent.shared_libraries.permissions import is_allowed, is_consequential
from financial_processing_agent.state.run_state import RunState


class ToolDenied(PermissionError):
    """Raised when a tool is not allowed, over budget, or submit is not approved."""


def assert_submit_allowed(state: RunState, tool_name: str) -> None:
    """Block submit_finance_decision unless status is APPROVED and an idempotency key exists."""
    if not is_consequential(tool_name):
        return
    if state.status != "APPROVED":
        raise ToolDenied(
            f"{tool_name} is deny-by-default until human approval; status={state.status}"
        )
    if not state.approval.idempotency_key:
        raise ToolDenied("submit requires an approval idempotency key")


def before_tool(state: RunState, tool_name: str) -> None:
    """
    Allow-list, budget, then consequential-tool gate.

    Call this before every tool invocation (Workflow._call does). Unknown
    tool names and a 12-call budget both raise ToolDenied so a looping
    agent cannot exhaust APIs or invent a posting tool.
    """
    if not is_allowed(tool_name):
        raise ToolDenied(f"tool not on allow-list: {tool_name}")
    if state.tool_call_count >= 12:
        raise ToolDenied("tool-call budget exceeded")
    assert_submit_allowed(state, tool_name)
