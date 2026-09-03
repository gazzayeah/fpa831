"""Minimal sub-agents: parallel gather (read-only) then coded recommend. Not specialist LLMs."""

from financial_processing_agent.sub_agents.gather import READ_ONLY_TOOL_NAMES
from financial_processing_agent.sub_agents.recommend import RECOMMEND_INSTRUCTION

__all__ = ["READ_ONLY_TOOL_NAMES", "RECOMMEND_INSTRUCTION"]
