resource "google_redis_instance" "doodleops-redis" {
  name           = "doodleops-redis"
  tier           = "BASIC"
  redis_version  = "REDIS_6_X"
  memory_size_gb = 1
  replica_count  = 0
  read_replicas_mode = "READ_REPLICAS_DISABLED"
  region         = var.GCP_REGION
  location_id    = var.GCP_ZONE
  connect_mode = "PRIVATE_SERVICE_ACCESS"

  authorized_network = google_compute_network.vpc_network.id

  lifecycle {
    prevent_destroy = false
  }
  depends_on = [
    google_compute_network.vpc_network,
    google_service_networking_connection.private_vpc_connection
  ]
}