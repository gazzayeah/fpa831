# Tenant Terraform (fpa831)

Owns tenant resources that are not in `iac_main`. Today that is the Agent
Engine staging bucket (`google_storage_bucket.agent_staging`). Project APIs,
WIF, `terraform-sa`, and `agent-dev` stay in the platform root.

## State

Same bucket as the platform root, different prefix:

| Root | Backend file | Prefix |
| --- | --- | --- |
| `iac_main` platform | `iac_main/iac/terraform/state_backend/dev.hcl` | `showcase/dev` |
| this tenant | `state_backend/dev.hcl` | `fpa831/dev` |

```bash
cd iac/terraform
terraform init -backend-config=state_backend/dev.hcl -reconfigure
terraform plan -var-file=variables/dev.tfvars
```

Do not init this directory with `prefix = "showcase/dev"`.

## Authentication

GitHub Actions federates through the platform WIF pool (`github-pool` /
`github-provider`) as `terraform-sa`. `gazzayeah/fpa831` must be listed in
`iac_main` `github_repositories` and applied there first.

Local administration:

```bash
gcloud auth application-default login
export TF_VAR_tf_service_account="terraform-sa@light-operator-364723.iam.gserviceaccount.com"
terraform plan -var-file=variables/dev.tfvars
```

## CI

[`.github/workflows/tenant_iac_deployment.yaml`](../../.github/workflows/tenant_iac_deployment.yaml)
plans on pull requests and applies on `main` / `workflow_dispatch`, using the
same reusable plan/apply jobs as `iac_main`.
