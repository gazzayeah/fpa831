# Tenant infrastructure

Application-scoped Terraform for the financial-processing agent. Shared
project foundations (APIs, WIF, `terraform-sa`, state bucket, VPC, agent
runtime SA) stay in [`iac_main/iac/terraform`](https://github.com/gazzayeah/iac_main/tree/main/iac/terraform).

This root does not recreate those resources. Tenant state uses a separate
GCS prefix so it cannot collide with the platform state.

See [`terraform/README.md`](terraform/README.md).
