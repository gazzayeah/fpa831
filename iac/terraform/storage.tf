# GCS staging bucket for Vertex Agent Engine package upload.
# terraform-sa already has project roles/storage.admin from iac_main, so it
# can write objects. The bucket is tenant-owned so IRCC CDC and Terraform
# state are not mixed with agent tarballs.

resource "google_storage_bucket" "agent_staging" {
  project                     = var.gcp_project_id
  name                        = "${var.gcp_project_id}-fpa831-agent-${var.environment}"
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
}

resource "google_storage_bucket_iam_member" "agent_staging_deployer" {
  bucket = google_storage_bucket.agent_staging.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:terraform-sa@${var.gcp_project_id}.iam.gserviceaccount.com"
}
