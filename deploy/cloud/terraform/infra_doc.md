# Resources that we deploy with Terraform

### 1. VPC Network

This resource creates a VPC network without automatically creating subnetworks. 
This is useful for custom network topologies, allowing granular control over 
our network's design.
```bash
resource "google_compute_network" "vpc_network" {
  name                    = "doodleops-vpc"
  auto_create_subnetworks = false
}
```

### 2. Global Address (Private IP Range)

This resource reserves an IP range within our VPC for use by Google-managed 
services, such as Cloud SQL. This is necessary because these services need to be 
allocated IP addresses within our VPC to communicate privately and securely with 
other resources in our VPC. This setup is part of setting up VPC peering between 
our VPC and the Google-managed services VPC.

```bash
resource "google_compute_global_address" "private_ip_range" {
  name          = "google-managed-services-doodleops-vpc"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc_network.id
}
```

### 3. Service Networking Connection (Private VPC Connection)

This resource establishes a VPC peering connection between our VPC and the Google
services that use the reserved IP range. VPC peering is a networking connection 
between two VPCs that enables us to route traffic between them using private IP 
addresses. In this case, it's required for Google-managed services to securely 
access our VPC's resources.

```bash
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]
}
```

### 4. Serverless VPC Access Connector

This connector is necessary for serverless products like Cloud Run to access 
resources in our VPC, such as Redis and Cloud SQL, which are not publicly
accessible over the Internet. It acts as a bridge between the serverless 
environment and our VPC.

```bash
resource "google_vpc_access_connector" "serverless_connector" {
  name          = "serverless-connector"
  project       = var.GCP_PROJECT_ID
  region        = var.GCP_REGION
  network       = google_compute_network.vpc_network.id
  ip_cidr_range = "10.8.0.0/28"
}
```

### 5. Subnetwork

By creating subnetworks in specific regions, we can ensure that our resources 
are deployed close to each other to minimize latency and comply with data 
residency requirements.

Network Security and Policies: Subnetworks allow us to apply firewall rules and 
routing rules to segments of our network, enhancing security and traffic 
management.

```bash
resource "google_compute_subnetwork" "vpc_subnetwork" {
  name          = "doodleops-subnet"
  ip_cidr_range = "10.8.1.0/24"
  region        = var.GCP_REGION
  network       = google_compute_network.vpc_network.id
}
```