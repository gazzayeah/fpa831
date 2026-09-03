output "gcp_project_id" {
  description = "Shared GCP project used by this tenant root."
  value       = data.google_project.current.project_id
}

output "gcp_project_number" {
  description = "Numeric project number for WIF provider paths."
  value       = data.google_project.current.number
}

output "environment" {
  description = "Tenant environment label."
  value       = var.environment
}
