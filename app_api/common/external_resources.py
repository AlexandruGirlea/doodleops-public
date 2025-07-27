import json
import uuid
import base64
import logging
from datetime import datetime

import httpx
from google.cloud import pubsub_v1

from core.settings import ENV_MODE, GCP_PROJECT_ID
from app_ai.views.v1.urls import app_ai_v1_urls
from app_ai.cloud_run_container_app_ai.v1.common.pub_sub_schema import (
	TwilioPublisherMsg
)

logger = logging.getLogger("APP_API_"+__name__)


class LocalPublishFuture:
	"""
	Mimics the future object returned by real Pub/Sub publishes.
	"""
	def __init__(self, message_id: str):
		self._message_id = message_id

	def result(self):
		"""
		In real Pub/Sub, this waits for the publish to complete.
		"""
		return self._message_id


class LocalPublisherClient:
	"""A mock PublisherClient"""

	def __init__(self, local_endpoint: str):
		self.local_endpoint = local_endpoint

	def topic_path(self, project: str, topic: str) -> str:
		return f"projects/{project}/topics/{topic}"

	def publish(
			self, topic: str, data: bytes, **kwargs
	) -> LocalPublishFuture:
		encoded_data = base64.b64encode(data).decode("utf-8")

		message_id = str(uuid.uuid4())
		publish_time = datetime.utcnow().isoformat() + "Z"
		event_body = {
			"message": {
				"data": encoded_data,
				"messageId": message_id,
				"publishTime": publish_time,
			},
			"subscription": "projects/fake-project/subscriptions/fake-sub",
		}

		headers = {
			"ce-id": str(uuid.uuid4()),
			"ce-source": topic,
			"ce-specversion": "1.0",
			"ce-type": "google.cloud.pubsub.topic.v1.messagePublished",
			"Content-Type": "application/json",
		}

		with httpx.Client() as client:

			response = client.post(
				self.local_endpoint, headers=headers, json=event_body,
				timeout=90  # seconds, because of LLM delay
			)
			response.raise_for_status()

		return LocalPublishFuture(message_id)


if ENV_MODE != "local":
	PUBLISHER = pubsub_v1.PublisherClient()
else:
	PUBLISHER = LocalPublisherClient(
			local_endpoint=app_ai_v1_urls["twilio_whatsapp_webhook"].url_target
		)


def publish_whatsapp_msg_to_pubsub(input_data: TwilioPublisherMsg) -> bool:

	topic_path = PUBLISHER.topic_path(
		topic="twilio",  # same as Terraform topic name needed for Eventarc
		project=GCP_PROJECT_ID
	)
	
	try:
		PUBLISHER.publish(
			topic=topic_path,
			data=json.dumps(input_data.model_dump()).encode("utf-8")
		)
	except Exception as e:
		logger.error(
			f"Phone number: {input_data.phone_number} encounter an error "
			f"when trying to publish to Pub/Sub. Response: {e}."
		)
		return False

	return True
