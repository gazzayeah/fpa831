"""
Recommend stage for the optional ADK graph.

``reconcile_case`` (code) is authoritative. If an LLM is attached, it may
only narrate that result — it must not recalculate or call submit.
"""

from financial_processing_agent.prompts import RECOMMEND_INSTRUCTION

__all__ = ["RECOMMEND_INSTRUCTION"]
