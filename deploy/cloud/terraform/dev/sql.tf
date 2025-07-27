resource "google_sql_database_instance" "doodleops-mysql" {
  name             = "doodleops-mysql"
  database_version = "MYSQL_8_0"
  region           = var.GCP_REGION

  settings {
    # this is for dev, in prod we will use a different tier and disk type
    tier = "db-f1-micro"
    disk_type = "PD_HDD"
    availability_type = "ZONAL"

    ip_configuration {
      ipv4_enabled    = true # Disables public IP only for prod
      private_network = google_compute_network.vpc_network.id
    }
  }

  deletion_protection = false
  depends_on          = [
    google_service_networking_connection.private_vpc_connection,
    google_compute_network.vpc_network
  ]
}

resource "google_sql_database" "doodleops-db" {
  name       = local.common_secrets.MYSQL_DATABASE
  instance   = google_sql_database_instance.doodleops-mysql.name
  depends_on = [
    google_sql_database_instance.doodleops-mysql,
    google_secret_manager_secret_version.app-common
  ]
}

resource "google_sql_user" "doodleops-db-user" {
  name       = local.common_secrets.MYSQL_USER
  instance   = google_sql_database_instance.doodleops-mysql.name
  password   = local.common_secrets.MYSQL_PASSWORD
  depends_on = [
    google_sql_database.doodleops-db,
    google_secret_manager_secret_version.app-common
  ]
}