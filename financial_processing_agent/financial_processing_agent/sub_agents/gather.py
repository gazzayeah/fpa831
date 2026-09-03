"""
Gather stage names for the optional ADK graph.

The coded path is ``Workflow._gather``, which calls these four tools in
sequence. This module only lists names so ``agent.py`` and docs stay aligned.
"""

READ_ONLY_TOOL_NAMES = (
    "retrieve_finance_documents",
    "get_vendor_record",
    "get_purchase_order",
    "check_invoice_history",
)
