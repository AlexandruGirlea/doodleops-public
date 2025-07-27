variable "GCP_PROJECT_NAME" {
  default = "doodleops-dev"
  description = "The GCP project name"
  type        = string
}

variable "GCP_PROJECT_ID" {
  default = "123"
  description = "The GCP project ID"
  type        = string
}

variable "GCP_REGION" {
  default = "us-central1"
  description = "The GCP region"
  type        = string
}

variable "GCP_ZONE" {
  default = "us-central1-c"
  description = "The GCP zone"
  type        = string
}

variable "SERVICE_ACCOUNT_KEY_PATH" {
  description = <<-EOD
  The path to the service account key file.
  This is automatically retrieved from the environment variable
  TF_VAR_SERVICE_ACCOUNT_KEY_PATH
  EOD
  type        = string
}

variable "DOCKER_REPO" {
  default = "us-central1-docker.pkg.dev/doodleops-dev/docker-repo"
  description = "The Docker repository to use"
  type        = string
}

variable "APP_WEB_VERSION" {
  default = "1.75.0"
  type = string
}

variable "APP_API_VERSION" {
  default = "1.68.0"
  type = string
}

variable "APP_DOCS_VERSION" {
  # we only use the MINOR and PATCH versions, the MAJOR version is in the image name
  default = "4.0"
  type = string
}

variable "APP_EPUB_VERSION" {
  # we only use the MINOR and PATCH versions, the MAJOR version is in the image name
  default = "4.0"
  type = string
}


variable "APP_IMAGES_VERSION" {
  # we only use the MINOR and PATCH versions, the MAJOR version is in the image name
  default = "5.0"
  type = string
}

variable "APP_PDF_VERSION" {
  # we only use the MINOR and PATCH versions, the MAJOR version is in the image name
  default = "12.0"
  type = string
}

variable "APP_AI_VERSION" {
  # we only use the MINOR and PATCH versions, the MAJOR version is in the image name
  default = "73.0"
  type = string
}

variable "SECRET_APP_COMMON_JSON" {
  default = ".env_app_common.json"
  type = string
  description = "This is a JSON with the secrets"
}

variable "SECRET_APP_WEB_JSON" {
  default = ".env_app_web.json"
  type = string
  description = "This is a JSON with the secrets"
}

variable "SECRET_APP_API_JSON" {
  default = ".env_app_api.json"
  type = string
  description = "This is a JSON with the secrets"
}

variable "SECRET_APP_API_APPS_JSON" {
  default = ".env_app_api_apps.json"
  type = string
  description = "This is a JSON with the secrets"
}

variable "SECRET_APP_API_APPS_AI_JSON" {
  default = ".env_app_api_apps_ai.json"
  type = string
  description = "This is a JSON with the secrets"
}