variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "gcp_project_id" {
  description = "Google Cloud Project ID. Shared with the platform root in iac_main."
  type        = string
}

variable "environment" {
  description = "Project environment (e.g. dev, prod)"
  type        = string
}

variable "tf_service_account" {
  type        = string
  description = "Optional SA to impersonate. Leave null in CI when WIF already authenticates as the Terraform SA."
  default     = null
  nullable    = true
}
