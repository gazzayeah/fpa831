provider "google" {
  project                     = var.gcp_project_id
  region                      = var.region
  billing_project             = var.gcp_project_id
  user_project_override       = true
  impersonate_service_account = var.tf_service_account
}

provider "google-beta" {
  project                     = var.gcp_project_id
  region                      = var.region
  billing_project             = var.gcp_project_id
  user_project_override       = true
  impersonate_service_account = var.tf_service_account
}

data "google_project" "current" {
  project_id = var.gcp_project_id
}
