resource "google_secret_manager_secret" "app-common" {
  secret_id = "app-common"

  replication {
    user_managed {
      replicas {
        location = var.GCP_REGION
      }
    }
  }
}

resource "google_secret_manager_secret" "app-web" {
  secret_id = "app-web"

  replication {
    user_managed {
      replicas {
        location = var.GCP_REGION
      }
    }
  }
}

resource "google_secret_manager_secret" "app-api" {
  secret_id = "app-api"
  replication {
    user_managed {
      replicas {
        location = var.GCP_REGION
      }
    }
  }
}


resource "google_secret_manager_secret" "app-api-apps" {
  secret_id = "app-api-apps"
  replication {
    user_managed {
      replicas {
        location = var.GCP_REGION
      }
    }
  }
}

resource "google_secret_manager_secret" "app-api-apps-ai" {
  secret_id = "app-api-apps-ai"
  replication {
    user_managed {
      replicas {
        location = var.GCP_REGION
      }
    }
  }
}

resource "google_secret_manager_secret" "app-celery-service-account-key" {
  secret_id = "app-celery-service-account-key"
  replication {
    user_managed {
      replicas {
        location = var.GCP_REGION
      }
    }
  }
}
##################################################################################

# resource is used to create the secret content
resource "google_secret_manager_secret_version" "app-common" {
  secret = google_secret_manager_secret.app-common.name

  secret_data = file("${path.module}/${var.SECRET_APP_COMMON_JSON}")

  lifecycle {
    # use true on production
    prevent_destroy = false
  }
}

resource "google_secret_manager_secret_version" "app-web" {
  secret = google_secret_manager_secret.app-web.name

  secret_data = file("${path.module}/${var.SECRET_APP_WEB_JSON}")

  lifecycle {
    # use true on production
    prevent_destroy = false
  }
}

resource "google_secret_manager_secret_version" "app-api" {
  secret = google_secret_manager_secret.app-api.name

  secret_data = file("${path.module}/${var.SECRET_APP_API_JSON}")

  lifecycle {
    # use true on production
    prevent_destroy = false
  }
}

resource "google_secret_manager_secret_version" "app-api-apps" {
  secret = google_secret_manager_secret.app-api-apps.name

  secret_data = file("${path.module}/${var.SECRET_APP_API_APPS_JSON}")

  lifecycle {
    # use true on production
    prevent_destroy = false
  }
}

resource "google_secret_manager_secret_version" "app-api-apps-ai" {
  secret = google_secret_manager_secret.app-api-apps-ai.name

  secret_data = file("${path.module}/${var.SECRET_APP_API_APPS_AI_JSON}")

  lifecycle {
    # use true on production
    prevent_destroy = false
  }
}

resource "google_secret_manager_secret_version" "app_celery_key_version" {
  secret      = google_secret_manager_secret.app-celery-service-account-key.id
  secret_data = base64decode(google_service_account_key.celery_terraform_json_key.private_key)
}

##################################################################################

# data is used to retrieve the secret content
data "google_secret_manager_secret_version" "app-common" {
  secret  = google_secret_manager_secret.app-common.id
  version = "latest"
  depends_on = [google_secret_manager_secret_version.app-common]
}

data "google_secret_manager_secret_version" "app-web" {
  secret  = google_secret_manager_secret.app-web.id
  version = "latest"
  depends_on = [google_secret_manager_secret_version.app-web]
}

data "google_secret_manager_secret_version" "app-api" {
  secret  = google_secret_manager_secret.app-api.id
  version = "latest"
  depends_on = [google_secret_manager_secret_version.app-api]
}

data "google_secret_manager_secret_version" "app-api-apps" {
  secret  = google_secret_manager_secret.app-api-apps.id
  version = "latest"
  depends_on = [google_secret_manager_secret_version.app-api-apps]
}

data "google_secret_manager_secret_version" "app-api-apps-ai" {
  secret  = google_secret_manager_secret.app-api-apps-ai.id
  version = "latest"
  depends_on = [google_secret_manager_secret_version.app-api-apps-ai]
}
##################################################################################

locals {

  common_secrets  = jsondecode(data.google_secret_manager_secret_version.app-common.secret_data)
  # Cloudflare IPs
  whitelist_ips_1 = [
    "103.21.244.0/22",
    "103.22.200.0/22",
    "103.31.4.0/22",
    "104.16.0.0/13",
    "104.24.0.0/14",
    "108.162.192.0/18",
    "131.0.72.0/22",
    "141.101.64.0/18",
    "162.158.0.0/15",
    "172.64.0.0/13",
  ]

  whitelist_ips_2 = [
    "173.245.48.0/20",
    "188.114.96.0/20",
    "190.93.240.0/20",
    "197.234.240.0/22",
    "198.41.128.0/17",
    "2400:cb00::/32",
    "2606:4700::/32",
    "2803:f800::/32",
    "2405:b500::/32",
    "2405:8100::/32",
  ]

  whitelist_ips_3 = [
    "2a06:98c0::/29",
    "2c0f:f248::/32"
  ]
}