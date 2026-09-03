# GitHub Actions workflows

Reusable Terraform workflows live at the top level of `.github/workflows/`
(GitHub does not reliably load nested workflow directories).

| File | Role |
| --- | --- |
| `terraform-plan.yaml` | Reusable plan workflow (`workflow_call`) |
| `terraform-apply.yaml` | Reusable apply workflow (`workflow_call`) |
| `tenant_iac_deployment.yaml` | Caller: plan/apply `iac/terraform` |

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

## Local Terraform

CI keeps `terraform fmt -recursive -check`.

```bash
cd iac/terraform
export TF_VAR_tf_service_account="terraform-sa@light-operator-364723.iam.gserviceaccount.com"
terraform init -backend-config=state_backend/dev.hcl -reconfigure
terraform plan -var-file=variables/dev.tfvars
```
