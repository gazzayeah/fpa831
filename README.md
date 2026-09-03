# fpa831 — Financial processing and RAG workflow agent

An internal accounts-payable assistant. Given an invoice case, it retrieves finance policy and related evidence, reconciles invoice / PO / receipt / vendor records in code, surfaces exceptions, and **stops for human approval** before any posting or payment.

This is a control-and-grounding exercise, not a chatbot.

**Grounding.** Conclusions are cited to retrieved chunks (document ID, version, relevance). Retrieved text is untrusted: supplier attachments and stale policy cannot override system rules or authorize payment. Totals and three-way match are deterministic in code, not free-form model arithmetic. The typed result separates sourced facts, calculations, inferences, unknowns, and actions.

**Control.** Bounded agent loop with a tool-call budget. Consequential tools are deny-by-default, approval-gated, and idempotent. Invalid model or tool output is retried, repaired, or failed explicitly. Runs persist so a reviewer can inspect, resume, and replay a duplicate approval as one decision.

Built to the take-home cases: valid match (FIN-001), duplicate (FIN-002), poisoned document (FIN-003), missing evidence (FIN-004), and duplicate approval callback (FIN-005).

## IaC and CI

Tenant Terraform lives in [`iac/terraform`](iac/terraform). Shared GCP
foundations (WIF, `terraform-sa`, state bucket) stay in `iac_main`. This
repo’s state prefix is `fpa831/dev`. GitHub Actions plan on pull request and
apply on `main`; see [`.github/workflows/README.md`](.github/workflows/README.md).
