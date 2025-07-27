# Create the main service account for the project

resource "google_service_account" "app-web" {
  account_id   = "service-account-app-web"
  display_name = "Service account for Cloud Run App WEB"
}

resource "google_service_account" "app-api" {
  account_id   = "service-account-app-api"
  display_name = "Service account for Cloud Run App API"
}
resource "google_service_account" "app-api-apps" {
  account_id   = "service-account-app-api-apps"
  display_name = "Service account for Cloud Run App API Apps"
}

resource "google_service_account" "app_celery" {
  account_id   = "service-account-app-celery"
  display_name = "Service account for Celery VM"
}

resource "google_service_account" "cloud_build" {
  account_id   = "cloud-build"
  display_name = "Cloud Build Service Account"
  project      = var.GCP_PROJECT_NAME
}

resource "google_service_account" "gcf_manager" {
  account_id   = "gcf-manager"
  display_name = "GCF Service Account and used for GDrive access"
}

##################################################################################
# Grant the new deployed service accounts access to specific secrets.

# web
resource "google_secret_manager_secret_iam_member" "app-web" {
  secret_id = google_secret_manager_secret.app-web.id
  role      = "roles/secretmanager.secretAccessor"
  member     = "serviceAccount:${google_service_account.app-web.email}"
  depends_on = [google_secret_manager_secret.app-web]
}

resource "google_secret_manager_secret_iam_member" "app-web-common" {
  secret_id = google_secret_manager_secret.app-common.id
  role      = "roles/secretmanager.secretAccessor"
  member     = "serviceAccount:${google_service_account.app-web.email}"
  depends_on = [google_secret_manager_secret.app-common]
}

# api
resource "google_secret_manager_secret_iam_member" "app-api" {
  secret_id = google_secret_manager_secret.app-api.id
  role      = "roles/secretmanager.secretAccessor"
  member     = "serviceAccount:${google_service_account.app-api.email}"
  depends_on = [google_secret_manager_secret.app-api]
}

resource "google_secret_manager_secret_iam_member" "app-api-common" {
  secret_id = google_secret_manager_secret.app-common.id
  role      = "roles/secretmanager.secretAccessor"
  member     = "serviceAccount:${google_service_account.app-api.email}"
  depends_on = [google_secret_manager_secret.app-common]
}

# api-apps
resource "google_secret_manager_secret_iam_member" "app-api-apps" {
  secret_id = google_secret_manager_secret.app-api-apps.id
  role      = "roles/secretmanager.secretAccessor"
  member     = "serviceAccount:${google_service_account.app-api-apps.email}"
  depends_on = [google_secret_manager_secret.app-api-apps]
}

resource "google_secret_manager_secret_iam_member" "app-api-apps-ai" {
  secret_id = google_secret_manager_secret.app-api-apps-ai.id
  role      = "roles/secretmanager.secretAccessor"
  member     = "serviceAccount:${google_service_account.app-api-apps.email}"
  depends_on = [google_secret_manager_secret.app-api-apps-ai]
}

# celery
resource "google_secret_manager_secret_iam_member" "celery_app_web" {
  secret_id = google_secret_manager_secret.app-web.id
  role      = "roles/secretmanager.secretAccessor"
  member     = "serviceAccount:${google_service_account.app_celery.email}"
  depends_on = [google_secret_manager_secret.app-web]
}

resource "google_secret_manager_secret_iam_member" "celery_app_common" {
  secret_id = google_secret_manager_secret.app-common.id
  role      = "roles/secretmanager.secretAccessor"
  member     = "serviceAccount:${google_service_account.app_celery.email}"
  depends_on = [google_secret_manager_secret.app-common]
}

resource "google_secret_manager_secret_iam_member" "celery_app_celery_service_account_key" {
  secret_id = google_secret_manager_secret.app-celery-service-account-key.id
  role      = "roles/secretmanager.secretAccessor"
  member     = "serviceAccount:${google_service_account.app_celery.email}"
  depends_on = [google_secret_manager_secret.app-common]
}

##################################################################################
# This is the service account key that will be used by the Celery VM
resource "google_service_account_key" "celery_terraform_json_key" {
  service_account_id = google_service_account.app_celery.name
}

##################################################################################
locals {
  app_web_roles = [
    "roles/cloudtrace.agent",
    "roles/recaptchaenterprise.agent"
  ]

  app_api_roles = [
    "roles/cloudtrace.agent",
    "roles/storage.admin",
    "roles/cloudtasks.enqueuer",
    "roles/run.invoker",
    "roles/pubsub.publisher",
  ]

  app_api_apps_roles = [
    "roles/cloudtrace.agent",
    "roles/cloudtrace.admin",
    "roles/logging.logWriter",
    "roles/aiplatform.user",
    "roles/storage.objectUser",
  ]

  cloud_build_roles = [
    "roles/artifactregistry.admin",
    "roles/redis.editor",
    "roles/run.admin",
    "roles/cloudsql.client",
    "roles/compute.instanceAdmin.v1",
    "roles/compute.networkAdmin",
    "roles/compute.osAdminLogin",
    "roles/compute.securityAdmin",
    "roles/compute.viewer",
    "roles/iap.tunnelResourceAccessor",
    "roles/logging.logWriter",
    "roles/secretmanager.secretAccessor",
    "roles/secretmanager.viewer",
    "roles/iam.serviceAccountUser",
    "roles/storage.admin",
    "roles/cloudtrace.agent"
  ]

  app_celery_roles = [
    "roles/artifactregistry.reader",
    "roles/container.admin",
    "roles/container.clusterAdmin",
    "roles/redis.admin",
    "roles/cloudsql.admin",
    "roles/cloudfunctions.admin",
    "roles/cloudfunctions.developer",
    "roles/storage.admin",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/cloudtrace.agent"
    ]
    # not yet used, we might use this in the future
    gcf_manager_roles = [
    "roles/cloudfunctions.admin",
    "roles/cloudfunctions.developer",
    "roles/cloudfunctions.invoker",
    "roles/run.invoker"
  ]
}

resource "google_project_iam_member" "app_web_roles" {
  for_each = toset(local.app_web_roles)
  project = var.GCP_PROJECT_NAME
  role    = each.value
  member  = "serviceAccount:${google_service_account.app-web.email}"
}

resource "google_project_iam_member" "app_api_roles" {
  for_each = toset(local.app_api_roles)
  project = var.GCP_PROJECT_NAME
  role    = each.value
  member  = "serviceAccount:${google_service_account.app-api.email}"
}

resource "google_project_iam_member" "app_api_apps_roles" {
  for_each = toset(local.app_api_apps_roles)
  project = var.GCP_PROJECT_NAME
  role    = each.value
  member  = "serviceAccount:${google_service_account.app-api-apps.email}"
}

resource "google_project_iam_member" "app_celery" {
  for_each = toset(local.app_celery_roles)
  project = var.GCP_PROJECT_NAME
  role    = each.value
  member  = "serviceAccount:${google_service_account.app_celery.email}"
}

resource "google_project_iam_member" "cloud_build_sa_roles" {
  for_each = toset(local.cloud_build_roles)
  project = var.GCP_PROJECT_NAME
  role    = each.value
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "gcf_manager_roles" {
  for_each = toset(local.gcf_manager_roles)
  project = var.GCP_PROJECT_NAME
  role    = each.value
  member  = "serviceAccount:${google_service_account.gcf_manager.email}"
}