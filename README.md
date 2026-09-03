# fpa831 — Financial processing and RAG workflow agent

An internal accounts-payable assistant. Given an invoice case, it retrieves finance policy and related evidence, reconciles invoice / PO / receipt / vendor records in code, surfaces exceptions, and **stops for human approval** before any posting or payment.

This is a control-and-grounding exercise, not a chatbot.

**Grounding.** Conclusions are cited to retrieved chunks (document ID, version, relevance). Retrieved text is untrusted: supplier attachments and stale policy cannot override system rules or authorize payment. Totals and three-way match are deterministic in code, not free-form model arithmetic. The typed result separates sourced facts, calculations, inferences, unknowns, and actions.

**Control.** Bounded agent loop with a tool-call budget. Consequential tools are deny-by-default, approval-gated, and idempotent. Invalid model or tool output is retried, repaired, or failed explicitly. Runs persist so a reviewer can inspect, resume, and replay a duplicate approval as one decision.

Built to the take-home cases: valid match (FIN-001), duplicate (FIN-002), poisoned document (FIN-003), missing evidence (FIN-004), and duplicate approval callback (FIN-005).

## Agent (local)

```bash
cd financial_processing_agent
python -m pytest
python -m financial_processing_agent.cli eval
python -m financial_processing_agent.cli start --fixture --case-id FIN-001
```

Mocks: vendor, PO, invoice history, and posting (`submit_finance_decision`). RAG is local over `docs/finance_rag_corpus/`. No live money movement.

## Design note

v1 is a **coded workflow** (`Workflow` in `financial_processing_agent/workflow.py`), not a chat loop. `start` gathers evidence, `reconcile_case` decides, then the run **pauses**. `approve` is the only path that may call `submit_finance_decision`. The optional ADK `SequentialAgent` in `agent.py` exposes the same tools for `adk run`; it does not own posting.

**Why arithmetic is not an LLM job.** FIN-POL-002 tolerances (goods: lower of AUD 50 or 1% of PO line; services: lower of AUD 100 or 2%) and duplicate fingerprints (FIN-POL-005) are `Decimal` code in `utils/matching.py` and `utils/duplicates.py`. The model must not re-total an invoice. Missing PO or receipt is `HOLD_FOR_INFORMATION`, not a guessed match (FIN-004).

**Why posting is deny-by-default.** `submit_finance_decision` is the only consequential tool. `callbacks/access.py` blocks it unless status is `APPROVED` and an idempotency key is set. The sandbox ledger returns the same `posting_reference` on replay (FIN-005). A recommendation of `APPROVE_FOR_POSTING` is not an approval.

**Why ADV-001 is still indexed.** Retrieval includes current policy, the superseded DFA (`FIN-POL-003-OLD`), the poisoned supplier note (`ADV-001`), and the travel distractor (`ADV-002`). Hits are evidence. `utils/injection.py` flags instruction-like language; FIN-003 must retrieve ADV-001, set injection flags, and **not** pay. Current DFA outranks the superseded matrix.

**Persistence.** Run state (citations, exceptions, recommendation, audit) is SQLite. `get` is inspectable after restart. Identity is `run_id` / `case_id` / `actor_id`, not a chat `user_id`. Ranking scores live on citations.

**CLI (brief operations).** `start`, `get`, `approve` / `reject`, `eval`. No HTTP layer in v1; the contract is the same.

### Deferred (on purpose)

- Agent Engine `deployment/deploy.py` and a live Gemini recommend step — local eval is the gate; deploy is the IRCC follow-on pattern.
- Specialist LLM subagents and policies 008–012 exception paths — not required to pass FIN-001–005.
- Vertex AI Search / BigQuery — the brief does not require a particular retriever.
- Moving `pyproject.toml` to the repo root — nicer for `uv` at root; the nested package is enough to run.

Timebox is 8 hours. Stop here and keep the control path reviewable.

## IaC and CI

Tenant Terraform lives in [`iac/terraform`](iac/terraform). Shared GCP
foundations (WIF, `terraform-sa`, state bucket) stay in `iac_main`. This
repo’s state prefix is `fpa831/dev`. GitHub Actions plan Terraform on
IaC pull requests, apply on `main`, and run **agent eval** (pytest +
FIN-001–005) when agent or corpus files change. See
[`.github/workflows/README.md`](.github/workflows/README.md).
