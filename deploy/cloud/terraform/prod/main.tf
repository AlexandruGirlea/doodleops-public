provider "google" {
  project     = var.GCP_PROJECT_NAME
  region      = var.GCP_REGION
  credentials =  var.SERVICE_ACCOUNT_KEY_PATH != "" ? file(var.SERVICE_ACCOUNT_KEY_PATH) : null
}

terraform {
  backend "gcs" {
    bucket = "tfstate-doodleops-prod"
    prefix = "terraform/state"
  }
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.44"
    }
  }
}