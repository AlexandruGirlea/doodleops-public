locals {
  common_template_vm_vars = {
    MYSQL_HOST          = google_sql_database_instance.doodleops-mysql.private_ip_address,
    REDIS_HOST          = google_redis_instance.doodleops-redis.host,
    GCP_PROJECT_ID      = var.GCP_PROJECT_ID,
  }
}

resource "google_compute_instance" "celery_beat_vm" {
  name         = "celery-beat-vm"
  machine_type = "f1-micro"
  zone         = var.GCP_ZONE

  boot_disk {
    initialize_params {
      image = "cos-cloud/cos-stable"
    }
  }

  network_interface {
    # Specifies the VPC by referencing its name
    network = google_compute_network.vpc_network.name
  }
  metadata_startup_script = templatefile("${path.module}/scripts/celery_vm_startup.sh", merge(
    local.common_template_vm_vars,
    {"VM_NAME" : "dev_celery_beat_vm"}
  ))
  metadata = {
    google-logging-enabled = "true"
  }

  service_account {
    email  = google_service_account.app_celery.email
    scopes = ["cloud-platform",]
  }

  depends_on = [
    google_service_account.app_celery,
    google_cloud_run_v2_service.app-web,
    google_project_iam_member.app_celery,
    google_secret_manager_secret_iam_member.celery_app_web,
    google_secret_manager_secret_iam_member.celery_app_common,
  ]
}

resource "google_compute_instance" "celery_worker_vm" {
  name         = "celery-worker-vm"
  machine_type = "e2-medium"
  zone         = var.GCP_ZONE
  allow_stopping_for_update  = true

  boot_disk {
    initialize_params {
      image = "cos-cloud/cos-stable"
    }
  }

  network_interface {
    # Specifies the VPC by referencing its name
    network = google_compute_network.vpc_network.name
  }
  metadata_startup_script = templatefile("${path.module}/scripts/celery_vm_startup.sh", merge(
    local.common_template_vm_vars,
    {"VM_NAME" : "dev_celery_worker_vm"}
  ))
  metadata = {
    google-logging-enabled = "true"
  }

  service_account {
    email  = google_service_account.app_celery.email
    scopes = ["cloud-platform",]
  }

  depends_on = [
    google_service_account.app_celery,
    google_cloud_run_v2_service.app-web,
    google_project_iam_member.app_celery,
    google_secret_manager_secret_iam_member.celery_app_web,
    google_secret_manager_secret_iam_member.celery_app_common,
  ]
}