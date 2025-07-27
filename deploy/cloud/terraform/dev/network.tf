resource "google_compute_network" "vpc_network" {
  name                    = "doodleops-vpc"
}

resource "google_compute_global_address" "private_ip_range" {
  name          = "google-managed-services-doodleops-vpc"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc_network.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]
}


resource "google_vpc_access_connector" "serverless_connector" {
  # used to enable serverless services within GCP
  # (like Cloud Run, App Engine, and Cloud Functions) to directly access resources
  # in a Virtual Private Cloud (VPC) network.
  name          = "serverless-connector"
  project       = var.GCP_PROJECT_NAME
  region        = var.GCP_REGION
  network       = google_compute_network.vpc_network.id
  ip_cidr_range = "10.8.0.0/28"
}

# Create a Regional static IP address
resource "google_compute_global_address" "default" {
  name   = "doodleops-dev-ip"
}

##################################################################################
# we need to provide VPC access to the internet for the Cloud Run services
resource "google_compute_router" "doodleops-router" {
  name    = "doodleops-router"
  region  = var.GCP_REGION
  network = google_compute_network.vpc_network.name
}

resource "google_compute_router_nat" "doodleops-nat" {
  name                               = "doodleops-nat"
  router                             = google_compute_router.doodleops-router.name
  region                             = google_compute_router.doodleops-router.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}


##################################################################################
# used for connecting Load Balancer to the Cloud Run service
resource "google_compute_region_network_endpoint_group" "app-web-neg" {
  name                  = "app-web-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.GCP_REGION
  cloud_run {
    service = google_cloud_run_v2_service.app-web.name
  }
}

resource "google_compute_region_network_endpoint_group" "app-api-neg" {
  name                  = "app-api-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.GCP_REGION
  cloud_run {
    service = google_cloud_run_v2_service.app-api.name
  }
}

##################################################################################
resource "google_compute_security_policy" "whitelist-cloudflare-only" {
  name = "whitelist-cloudflare-only"

  rule {
    action   = "deny(403)"
    priority = "247483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "default deny rule"
  }

  # we got the IP's from here https://www.cloudflare.com/ips/
  dynamic "rule" {
    for_each = [local.whitelist_ips_1, local.whitelist_ips_2, local.whitelist_ips_3]
    iterator = ip_group
    content {
      action   = "allow"
      priority = 1000 + ip_group.key
      match {
        versioned_expr = "SRC_IPS_V1"
        config {
          src_ip_ranges = ip_group.value
        }
      }
    }
  }
}

##################################################################################
# this gives the Load Balancer access to the Cloud Run service
resource "google_compute_backend_service" "app-web-backend" {
  name        = "app-web-backend"
  protocol    = "HTTP"
  security_policy = google_compute_security_policy.whitelist-cloudflare-only.id

  backend {
    group = google_compute_region_network_endpoint_group.app-web-neg.id
  }
}

resource "google_compute_backend_service" "app-api-backend" {
  name        = "app-api-backend"
  protocol    = "HTTP"
  log_config {
    enable = true
  }
  security_policy = google_compute_security_policy.whitelist-cloudflare-only.id

  backend {
    group = google_compute_region_network_endpoint_group.app-api-neg.id
  }
}

##################################################################################
resource "google_compute_url_map" "url-map" {
  name            = "url-map"

  default_service = google_compute_backend_service.app-web-backend.id

  host_rule {
    hosts        = ["dev.doodleops.com"]
    path_matcher = "app-web"
  }

  host_rule {
    hosts        = ["dev-api.doodleops.com"]
    path_matcher = "app-api"
  }

  host_rule {
    hosts        = ["dev-static.doodleops.com"]
    path_matcher = "static"
  }

  host_rule {
    hosts        = ["dev-temp-files.doodleops.com"]
    path_matcher = "temp-api-files"
  }

  path_matcher {
    name            = "app-web"
    default_service = google_compute_backend_service.app-web-backend.id
  }

  path_matcher {
    name            = "app-api"
    default_service = google_compute_backend_service.app-api-backend.id
  }

    path_matcher {
    name            = "static"
    default_service = google_compute_backend_bucket.cdn.id
  }

  path_matcher {
    name            = "temp-api-files"
    default_service = google_compute_backend_bucket.temp_api_files_bucket.id
  }
}

##################################################################################
resource "google_compute_managed_ssl_certificate" "managed-ssl-cert" {
  name    = "managed-ssl-cert"
  managed {
    domains = ["dev-api.doodleops.com", "dev.doodleops.com", "dev-static.doodleops.com"]
  }
}

##################################################################################

# this receives the traffic from the Load Balancer for all https traffic
resource "google_compute_target_https_proxy" "default" {
  name             = "https-lb-proxy"
  url_map          = google_compute_url_map.url-map.id
  ssl_certificates = [google_compute_managed_ssl_certificate.managed-ssl-cert.id]
}

# This is the entry point for the Load Balancer
resource "google_compute_global_forwarding_rule" "default_https" {
  name       = "https-content-rule"
  target     = google_compute_target_https_proxy.default.id
  port_range = "443"
  ip_address = google_compute_global_address.default.address
}