"""Workflow eval: all five take-home cases must pass without a live LLM."""

from financial_processing_agent.evaluation import run_evaluation
from financial_processing_agent.tools.submit_finance_decision import reset_postings
from financial_processing_agent.utils.run_store import RunStore
from financial_processing_agent.workflow import Workflow


def test_eval_cases(tmp_path):
    """Run FIN-001–005 against an isolated sqlite store."""
    reset_postings()
    results = run_evaluation(workflow=Workflow(store=RunStore(tmp_path / "runs.sqlite")))
    failed = [item["case_id"] for item in results if not item["pass"]]
    assert failed == [], results
