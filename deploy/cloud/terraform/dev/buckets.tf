resource "google_storage_bucket" "static-files-doodleops" {
  name          = "static-files-doodleops"
  location      = "US"
  force_destroy = true
  uniform_bucket_level_access = true

  website {
    not_found_page   = "404.html"
  }

  cors {
    origin = ["https://dev.doodleops.com"]
    method = ["GET", "HEAD"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
}

resource "google_compute_backend_bucket" "cdn" {
  name        = "cdn"
  bucket_name = google_storage_bucket.static-files-doodleops.name

  enable_cdn = true
}

resource "google_storage_bucket_iam_binding" "public-read-binding" {
  bucket = google_storage_bucket.static-files-doodleops.name
  role   = "roles/storage.objectViewer"

  members = [
    "allUsers",
  ]
}

resource "google_storage_bucket" "temp_api_files_bucket" {
  name          = "dev-temp-api-files-bucket"
  location      = var.GCP_REGION

  force_destroy = true
  uniform_bucket_level_access = true

  cors {
    origin          = ["https://dev-temp-files.doodleops.com"]
    method          = ["GET", "HEAD"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 1
    }
  }

  website {
    not_found_page   = "404.html"
  }
}

resource "google_compute_backend_bucket" "temp_api_files_bucket" {
  name        = "dev-temp-api-files-bucket"
  bucket_name = google_storage_bucket.temp_api_files_bucket.name
}

resource "google_storage_bucket_iam_binding" "public_temp_api_files_bucket" {
  bucket = google_storage_bucket.temp_api_files_bucket.name
  role   = "roles/storage.objectViewer"

  members = [
    "allUsers",
  ]
}

# bucket for hosting ML models
resource "google_storage_bucket" "ml-models" {
  name          = "dev-ml-models-and-resources"
  location      = var.GCP_REGION
  force_destroy = true
  uniform_bucket_level_access = true
}