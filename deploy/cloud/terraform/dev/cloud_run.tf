resource "google_cloud_run_v2_service" "app-web" {
  name     = "app-web"
  location = var.GCP_REGION
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  depends_on = [
    google_vpc_access_connector.serverless_connector,
    google_secret_manager_secret.app-common,
    google_secret_manager_secret.app-web,
    google_service_account.app-web,
    google_redis_instance.doodleops-redis,
    google_sql_user.doodleops-db-user,
    google_redis_instance.doodleops-redis,
  ]

  template {
    containers {
      image = "${var.DOCKER_REPO}/app_web:${var.APP_WEB_VERSION}"

      resources {
        cpu_idle = true
        limits = {
          cpu    = "1000m"
          memory = "2Gi"
        }
      }

      env {
        name  = "ENV_MODE"
        value = "dev"
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.GCP_PROJECT_ID
      }

      env {
        name  = "MYSQL_HOST"
        value = google_sql_database_instance.doodleops-mysql.private_ip_address
      }

      env {
        name  = "REDIS_HOST"
        value = google_redis_instance.doodleops-redis.host
      }
    }

    service_account = google_service_account.app-web.email
    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    vpc_access {
      # Use the VPC Connector
      connector = google_vpc_access_connector.serverless_connector.id
      # all egress from the service should go through the VPC Connector
      egress = "ALL_TRAFFIC"
    }
  }

  # this is because there is a discrepancy between the Terraform deployment and
  # the CI/CD pipeline deployment which is done using `gcloud` CLI
  lifecycle {
    prevent_destroy = false  # set to "true" in production
    ignore_changes = [
      client,
      client_version,
    ]
  }
}

resource "google_cloud_run_v2_service" "app-api" {
  name     = "app-api"
  location = var.GCP_REGION
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  depends_on = [
    google_vpc_access_connector.serverless_connector,
    google_secret_manager_secret.app-common,
    google_secret_manager_secret.app-api,
    google_service_account.app-api,
    google_sql_user.doodleops-db-user,
    google_redis_instance.doodleops-redis,
  ]

  template {
    containers {
      image = "${var.DOCKER_REPO}/app_api:${var.APP_API_VERSION}"
      resources {
        cpu_idle = true
        limits = {
          memory = "1Gi"
          cpu    = "1000m"
        }
      }

      env {
        name  = "ENV_MODE"
        value = "dev"
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.GCP_PROJECT_ID
      }

      env {
        name  = "REDIS_HOST"
        value = google_redis_instance.doodleops-redis.host
      }

      env {
        name  = "MYSQL_HOST"
        value = google_sql_database_instance.doodleops-mysql.private_ip_address
      }

    }

    service_account = google_service_account.app-api.email
    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    vpc_access {
      # Use the VPC Connector
      connector = google_vpc_access_connector.serverless_connector.id
      # all egress from the service should go through the VPC Connector
      egress = "ALL_TRAFFIC"
    }
  }
  lifecycle {
    prevent_destroy = false  # set to "true" in production
    ignore_changes = [
      client,
      client_version,
    ]
  }
}

resource "google_cloud_run_v2_service" "app-docs-v1" {
  name     = "app-docs-v1"
  location = var.GCP_REGION
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  depends_on = [
    google_cloud_run_v2_service.app-api,
    google_secret_manager_secret.app-api-apps,
    google_service_account.app-api-apps,
  ]

  template {
    containers {
      image = "${var.DOCKER_REPO}/app_docs_v1:${var.APP_DOCS_VERSION}"
      resources {
        cpu_idle = true
        limits = {
          cpu    = "1000m"
          memory = "1Gi"
        }
      }

      env {
        name  = "ENV_MODE"
        value = "dev"
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.GCP_PROJECT_ID
      }

    }

    service_account = google_service_account.app-api-apps.email
    scaling {
      max_instance_count = 5
      min_instance_count = 0
    }

    vpc_access {
      connector = google_vpc_access_connector.serverless_connector.id
      egress = "ALL_TRAFFIC"
    }
  }
  lifecycle {
    prevent_destroy = false  # set to "true" in production
    ignore_changes = [
      client,
      client_version,
    ]
  }
}

resource "google_cloud_run_v2_service" "app-epub-v1" {
  name     = "app-epub-v1"
  location = var.GCP_REGION
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  depends_on = [
    google_cloud_run_v2_service.app-api,
    google_secret_manager_secret.app-api-apps,
    google_service_account.app-api-apps,
  ]

  template {
    containers {
      image = "${var.DOCKER_REPO}/app_epub_v1:${var.APP_EPUB_VERSION}"
      resources {
        cpu_idle = true
        limits = {
          cpu    = "1000m"
          memory = "1Gi"
        }
      }

      env {
        name  = "ENV_MODE"
        value = "dev"
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.GCP_PROJECT_ID
      }

    }

    service_account = google_service_account.app-api-apps.email
    scaling {
      max_instance_count = 5
      min_instance_count = 0
    }

    vpc_access {
      connector = google_vpc_access_connector.serverless_connector.id
      egress = "ALL_TRAFFIC"
    }
  }
  lifecycle {
    prevent_destroy = false  # set to "true" in production
    ignore_changes = [
      client,
      client_version,
    ]
  }
}

resource "google_cloud_run_v2_service" "app-images-v1" {
  name     = "app-images-v1"
  location = var.GCP_REGION
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  depends_on = [
    google_cloud_run_v2_service.app-api,
    google_secret_manager_secret.app-api-apps,
    google_service_account.app-api-apps,
  ]

  template {
    containers {
      image = "${var.DOCKER_REPO}/app_images_v1:${var.APP_IMAGES_VERSION}"
      resources {
        cpu_idle = true
        limits = {
          cpu    = "2000m"
          memory = "2Gi"
        }
      }

      env {
        name  = "ENV_MODE"
        value = "dev"
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.GCP_PROJECT_ID
      }

    }

    service_account = google_service_account.app-api-apps.email
    scaling {
      max_instance_count = 5
      min_instance_count = 0
    }

    vpc_access {
      connector = google_vpc_access_connector.serverless_connector.id
      egress = "ALL_TRAFFIC"
    }
  }
  lifecycle {
    prevent_destroy = false  # set to "true" in production
    ignore_changes = [
      client,
      client_version,
    ]
  }
}

resource "google_cloud_run_v2_service" "app-pdf-v1" {
  name     = "app-pdf-v1"
  location = var.GCP_REGION
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  depends_on = [
    google_cloud_run_v2_service.app-api,
    google_secret_manager_secret.app-api-apps,
    google_service_account.app-api-apps,
  ]

  template {
    containers {
      image = "${var.DOCKER_REPO}/app_pdf_v1:${var.APP_PDF_VERSION}"
      resources {
        cpu_idle = true
        limits = {
          cpu    = "2000m"
          memory = "2Gi"
        }
      }

      env {
        name  = "ENV_MODE"
        value = "dev"
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.GCP_PROJECT_ID
      }

    }

    service_account = google_service_account.app-api-apps.email
    scaling {
      max_instance_count = 5
      min_instance_count = 0
    }

    vpc_access {
      connector = google_vpc_access_connector.serverless_connector.id
      egress = "ALL_TRAFFIC"
    }
  }
  lifecycle {
    prevent_destroy = false  # set to "true" in production
    ignore_changes = [
      client,
      client_version,
    ]
  }
}

resource "google_cloud_run_v2_service" "app-ai-v1" {
  name     = "app-ai-v1"
  location = var.GCP_REGION
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  depends_on = [
    google_cloud_run_v2_service.app-api,
    google_secret_manager_secret.app-api-apps,
    google_service_account.app-api-apps,
  ]

  template {
    containers {
      image = "${var.DOCKER_REPO}/app_ai_v1:${var.APP_AI_VERSION}"
      resources {
        cpu_idle = true
        limits = {
          cpu    = "2000m"
          memory = "4Gi"
        }
      }

      env {
        name  = "ENV_MODE"
        value = "dev"
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.GCP_PROJECT_ID
      }

      env {
        name  = "SECRET_MANAGER_NAME"
        value = google_secret_manager_secret.app-api-apps-ai.name
      }

      env {
        name  = "REDIS_HOST"
        value = google_redis_instance.doodleops-redis.host
      }

      env {
        name  = "EVENTARC_SERVICE_ACCOUNT"
        value = google_service_account.app-api.email
      }
    }

    service_account = google_service_account.app-api-apps.email
    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    vpc_access {
      connector = google_vpc_access_connector.serverless_connector.id
      egress = "ALL_TRAFFIC"
    }
  }
  lifecycle {
    prevent_destroy = false
    ignore_changes = [
      client,
      client_version,
    ]
  }
}


output "Attention-Please-Set-Annotation-For-Ingress-Load-Balancer" {
  # EOF
  value = <<EOF
    In Cloud Run -> Services -> app-api & app-web -> Networking -> choose Internal
    and Cloud Load Balancing. This will change the Cloud Run YAML file to:

    "run.googleapis.com/ingress"        = "internal-and-cloud-load-balancing"
    "run.googleapis.com/ingress-status" = "internal-and-cloud-load-balancing"

This needs to be done manually as it is not yet supported by the provider.
    EOF

  depends_on = [google_cloud_run_v2_service.app-api]
}

resource "google_cloud_run_v2_service_iam_member" "allow-public-app-web_invoker" {
  name  = google_cloud_run_v2_service.app-web.name
  location = var.GCP_REGION
  project  = var.GCP_PROJECT_ID
  role     = "roles/run.invoker"
  member   = "allUsers"

  depends_on = [google_cloud_run_v2_service.app-web]
}

resource "google_cloud_run_v2_service_iam_member" "allow-public-app-api_invoker" {
  name  = google_cloud_run_v2_service.app-api.name
  location = var.GCP_REGION
  project  = var.GCP_PROJECT_ID
  role     = "roles/run.invoker"
  member   = "allUsers"

  depends_on = [google_cloud_run_v2_service.app-api]
}

resource "google_cloud_run_v2_service_iam_member" "allow-public-app-docs-v1_invoker" {
  name  = google_cloud_run_v2_service.app-docs-v1.name
  location = var.GCP_REGION
  project  = var.GCP_PROJECT_ID
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.app-api.email}"
}

resource "google_cloud_run_v2_service_iam_member" "allow-public-app-epub-v1_invoker" {
  name  = google_cloud_run_v2_service.app-epub-v1.name
  location = var.GCP_REGION
  project  = var.GCP_PROJECT_ID
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.app-api.email}"
}

resource "google_cloud_run_v2_service_iam_member" "allow-public-app-images-v1_invoker" {
  name  = google_cloud_run_v2_service.app-images-v1.name
  location = var.GCP_REGION
  project  = var.GCP_PROJECT_ID
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.app-api.email}"
}

resource "google_cloud_run_v2_service_iam_member" "allow-public-app-pdf-v1_invoker" {
  name  = google_cloud_run_v2_service.app-pdf-v1.name
  location = var.GCP_REGION
  project  = var.GCP_PROJECT_ID
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.app-api.email}"
}

resource "google_cloud_run_v2_service_iam_member" "allow-public-app-ai-v1_invoker" {
  name  = google_cloud_run_v2_service.app-ai-v1.name
  location = var.GCP_REGION
  project  = var.GCP_PROJECT_ID
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.app-api.email}"
}