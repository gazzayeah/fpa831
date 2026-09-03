"""
CLI for the four required operations: start, get, approve/reject, eval.

    python -m financial_processing_agent.cli eval
    python -m financial_processing_agent.cli start --fixture --case-id FIN-001
"""

from __future__ import annotations

import argparse
import json
import sys

from financial_processing_agent.evaluation import run_evaluation
from financial_processing_agent.shared_libraries.schemas import CaseRequest
from financial_processing_agent.workflow import Workflow


def main(argv: list[str] | None = None) -> int:
    """
    Parse argv and dispatch to Workflow / evaluation.

    Commands: start, get, approve, reject, eval. ``eval`` is the take-home
    scorecard and returns exit code 1 if any FIN-00x case fails.
    """
    parser = argparse.ArgumentParser(description="Financial processing agent CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="Create a run from a case or fixture id")
    start.add_argument("--case-id", required=True)
    start.add_argument("--invoice-reference")
    start.add_argument("--vendor-id")
    start.add_argument("--amount")
    start.add_argument("--currency", default="AUD")
    start.add_argument("--po-id", default="")
    start.add_argument("--notes", default="")
    start.add_argument("--fixture", action="store_true", help="Load FIN-00x fixture")

    get_run = sub.add_parser("get", help="Get run status, state, result, audit")
    get_run.add_argument("run_id")

    approve = sub.add_parser("approve", help="Approve a pending posting")
    approve.add_argument("run_id")
    approve.add_argument("--actor", default="approver")
    approve.add_argument("--idempotency-key", required=True)

    reject = sub.add_parser("reject", help="Reject a pending posting")
    reject.add_argument("run_id")
    reject.add_argument("--actor", default="approver")

    sub.add_parser("eval", help="Run FIN-001–005 and report pass/fail")

    args = parser.parse_args(argv)
    workflow = Workflow()

    if args.command == "start":
        if args.fixture:
            state = workflow.start_fixture(args.case_id)
        else:
            case = CaseRequest(
                case_id=args.case_id,
                invoice_reference=args.invoice_reference or args.case_id,
                vendor_id=args.vendor_id or "",
                amount=args.amount or "0",
                currency=args.currency,
                po_id=args.po_id,
                notes=args.notes,
            )
            state = workflow.start(case)
        print(json.dumps({"run_id": state.run_id, "status": state.status}, indent=2))
        return 0

    if args.command == "get":
        state = workflow.get(args.run_id)
        if state is None:
            print("not found", file=sys.stderr)
            return 1
        print(state.model_dump_json(indent=2))
        return 0

    if args.command == "approve":
        state = workflow.approve(args.run_id, args.actor, args.idempotency_key)
        print(json.dumps({"status": state.status, "posting": state.posting_reference}, indent=2))
        return 0

    if args.command == "reject":
        state = workflow.reject(args.run_id, args.actor)
        print(json.dumps({"status": state.status}, indent=2))
        return 0

    if args.command == "eval":
        results = run_evaluation()
        print(json.dumps(results, indent=2))
        return 0 if all(item["pass"] for item in results) else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
