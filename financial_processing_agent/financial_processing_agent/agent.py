"""
Optional ADK graph: gather (read-only tools) then recommend (reconcile_case only).

CLI and pytest use ``Workflow``, which does not need ADK. ``root_agent`` is
None if google-adk is not installed so unit tests stay model-free.
"""

from financial_processing_agent.prompts import GLOBAL_INSTRUCTION, RECOMMEND_INSTRUCTION
from financial_processing_agent.shared_libraries.settings import settings
from financial_processing_agent.tools import (
    check_invoice_history,
    get_purchase_order,
    get_vendor_record,
    reconcile_case,
    retrieve_finance_documents,
)

try:
    from google.adk.agents import Agent, SequentialAgent
except ImportError:  # pragma: no cover - ADK optional for unit tests
    gather_agent = None
    recommend_agent = None
    root_agent = None
else:
    # Interactive ``adk run`` graph only. Posting remains gated in Workflow.approve.
    gather_agent = Agent(
        model=settings.agent_model,
        name="gather_agent",
        description="Retrieve policy, vendor, PO, and invoice history.",
        instruction="Call read-only tools only. Do not submit a finance decision.",
        tools=[
            retrieve_finance_documents,
            get_vendor_record,
            get_purchase_order,
            check_invoice_history,
        ],
    )
    recommend_agent = Agent(
        model=settings.agent_model,
        name="recommend_agent",
        description="Recommend an AP outcome from reconciled evidence.",
        global_instruction=GLOBAL_INSTRUCTION,
        instruction=RECOMMEND_INSTRUCTION,
        tools=[reconcile_case],
    )
    root_agent = SequentialAgent(
        name="financial_processing_agent",
        description="Gather evidence then recommend. Posting is approval-gated in Workflow.",
        sub_agents=[gather_agent, recommend_agent],
    )
