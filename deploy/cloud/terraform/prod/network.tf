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

resource "google_compute_global_address" "private_ip_range_access_additional" {
  name          = "google-managed-services-doodleops-vpc-additional"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 19  # e.g., 10.0.0.0/19
  network       = google_compute_network.vpc_network.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [
    google_compute_global_address.private_ip_range.name,
    google_compute_global_address.private_ip_range_access_additional.name
  ]
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
  name   = "doodleops-prod-ip"
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
    priority = "2147483647"
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
    hosts        = ["doodleops.com"]
    path_matcher = "app-web"
  }

  host_rule {
    hosts        = ["api.doodleops.com"]
    path_matcher = "app-api"
  }

  host_rule {
    hosts        = ["static.doodleops.com"]
    path_matcher = "static"
  }

  host_rule {
    hosts        = ["temp-files.doodleops.com"]
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
resource "google_compute_managed_ssl_certificate" "managed-ssl-cert-new" {
  name    = "managed-ssl-cert-new"
  managed {
    domains = ["api.doodleops.com", "doodleops.com", "static.doodleops.com", "temp-files.doodleops.com"]
  }
}


##################################################################################

# this receives the traffic from the Load Balancer for all https traffic
resource "google_compute_target_https_proxy" "default" {
  name             = "https-lb-proxy"
  url_map          = google_compute_url_map.url-map.id
  ssl_certificates = [google_compute_managed_ssl_certificate.managed-ssl-cert-new.id]
}

# This is the entry point for the Load Balancer
resource "google_compute_global_forwarding_rule" "default_https" {
  name       = "https-content-rule"
  target     = google_compute_target_https_proxy.default.id
  port_range = "443"
  ip_address = google_compute_global_address.default.address
}

##################################################################################
# this is the entry point for the Load Balancer
resource "google_compute_firewall" "allow_http" {
  name    = "doodleops-vpc-allow-http"
  network = google_compute_network.vpc_network.name
  direction = "INGRESS"
  priority  = 1000

  allow {
    protocol = "tcp"
    ports    = ["80"]
  }

  source_ranges = ["0.0.0.0/0"]
}

resource "google_compute_firewall" "allow_https" {
  name    = "doodleops-vpc-allow-https"
  network = google_compute_network.vpc_network.name
  direction = "INGRESS"
  priority  = 1000

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }

  source_ranges = ["0.0.0.0/0"]
}
##################################################################################
# this is the entry point for the Load Balancer
resource "google_dns_managed_zone" "doodleops_dns_zone" {
  name     = "doodleops-dns-zone"
  dns_name = "doodleops.com."

   dnssec_config {
    state = "on"  # Enable DNSSEC
    default_key_specs {
      key_type    = "keySigning"
      algorithm   = "rsasha256"
      key_length  = 2048
    }
    default_key_specs {
      key_type    = "zoneSigning"
      algorithm   = "rsasha256"
      key_length  = 1024
    }
  }
}

resource "google_dns_record_set" "doodleops_com_ns" {
  managed_zone = google_dns_managed_zone.doodleops_dns_zone.name
  name         = "doodleops.com."
  type         = "NS"
  ttl          = 21600
  rrdatas      = [
    "ns-cloud-d1.googledomains.com.",
    "ns-cloud-d2.googledomains.com.",
    "ns-cloud-d3.googledomains.com.",
    "ns-cloud-d4.googledomains.com."
  ]
}

resource "google_dns_record_set" "doodleops_com_txt" {
  managed_zone = google_dns_managed_zone.doodleops_dns_zone.name
  name         = "doodleops.com."
  type         = "TXT"
  ttl          = 21600
  rrdatas = [
    "\"v=spf1 include:_spf.firebasemail.com ~all\"",
    "\"firebase=doodleops-prod\""
  ]
}

resource "google_dns_record_set" "doodleops_com_soa" {
  managed_zone = google_dns_managed_zone.doodleops_dns_zone.name
  name         = "doodleops.com."
  type         = "SOA"
  ttl          = 21600
  rrdatas      = [
    "ns-cloud-d1.googledomains.com. cloud-dns-hostmaster.google.com. 1 21600 3600 259200 300"
  ]
}