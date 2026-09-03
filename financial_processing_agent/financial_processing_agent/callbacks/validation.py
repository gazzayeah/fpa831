"""Validate model JSON into Recommendation. Invalid output must fail, not be trusted."""

from __future__ import annotations

from financial_processing_agent.shared_libraries.schemas import Recommendation


def parse_recommendation_json(raw: str) -> Recommendation:
    """Parse and schema-validate LLM JSON. Raises ValueError on malformed output."""
    import json

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed model output: {exc}") from exc
    return Recommendation.model_validate(data)
