resource "google_pubsub_topic" "twilio" {
  name = "twilio"
}

# this is the consumer "google_cloud_run_v2_service" "app-ai-v1"
resource "google_eventarc_trigger" "twilio" {
  name = "twilio"
  location = var.GCP_REGION
  project  = var.GCP_PROJECT_ID
  service_account = google_service_account.app-api.email
  destination {
    cloud_run_service {
        service = google_cloud_run_v2_service.app-ai-v1.name
        region  = google_cloud_run_v2_service.app-ai-v1.location
        path    = "/twilio-events/dispatch"
    }
  }
  transport {
    pubsub {
      topic = google_pubsub_topic.twilio.id
      # subscription = "optional-subscription-name"
    }
  }
  depends_on = [
    google_cloud_run_v2_service_iam_member.allow-public-app-ai-v1_invoker,
    google_pubsub_topic.twilio
  ]

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.pubsub.topic.v1.messagePublished"
  }
}