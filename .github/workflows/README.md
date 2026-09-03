# GitHub Actions workflows

Reusable Terraform workflows live at the top level of `.github/workflows/`
(GitHub does not reliably load nested workflow directories).

| File | Role |
| --- | --- |
| `terraform-plan.yaml` | Reusable plan workflow (`workflow_call`) |
| `terraform-apply.yaml` | Reusable apply workflow (`workflow_call`) |
| `tenant_iac_deployment.yaml` | Caller: plan/apply `iac/terraform` |
| `agent-eval.yaml` | pytest + FIN-001–005 CLI eval (no GCP) |

Copied from `iac_main` so this tenant repo can run CI without calling a
private reusable workflow in another repository. WIF identities stay in
`iac_main`: pool `github-pool`, provider `github-provider`, SA
`terraform-sa@light-operator-364723.iam.gserviceaccount.com`.

## `tenant_iac_deployment.yaml`

1. `config` job uses runtime `ENVIRONMENT_NAME` (default `dev`) and unprefixed GCP/TF env knobs
2. Backend/var-file paths are derived: `state_backend/${ENVIRONMENT_NAME}.hcl`, `variables/${ENVIRONMENT_NAME}.tfvars`
3. On **pull_request**: runs plan
4. On **push** to `main`/`master` or **workflow_dispatch**: runs plan, then apply
5. `workflow_dispatch` can override `ENVIRONMENT_NAME`

Apply `github_repositories` in `iac_main` **before** this workflow can
authenticate. Tenant state prefix is `fpa831/dev`, not `showcase/dev`.

Plan/apply mint a WIF access token as `terraform-sa` (`token_format:
access_token`) and pass it to Terraform as `GOOGLE_OAUTH_ACCESS_TOKEN`.
That avoids a second impersonation hop via the ADC credentials file, which
surfaces as `iam.serviceAccounts.getAccessToken` 403 on `terraform init`.

## `agent-eval.yaml`

Runs on pull request, push to `main`/`master`, and `workflow_dispatch`
when `financial_processing_agent/**`, `docs/finance_rag_corpus/**`, or
this workflow file change. Uses `uv` against the nested
`financial_processing_agent/pyproject.toml` (Python 3.12, `--extra dev`,
`--frozen`). No WIF: eval is deterministic and does not call a model.

`uv.lock` in that directory must be committed so `--frozen` is reproducible.

## Local Terraform

CI keeps `terraform fmt -recursive -check`.

```bash
cd iac/terraform
export TF_VAR_tf_service_account="terraform-sa@light-operator-364723.iam.gserviceaccount.com"
terraform init -backend-config=state_backend/dev.hcl -reconfigure
terraform plan -var-file=variables/dev.tfvars
```
