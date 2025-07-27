import time
import logging
from typing import Optional

from google.genai import types

from llm_graph.utils.llm_models import genai_client
from common.other import (
	upload_resp_file_content_to_bucket, random_name_generator, download_image
)


logger = logging.getLogger("APP_AI_V1_" + __name__)


def generate_video(prompt: str, image_url: str = None) -> Optional[str]:
	if not genai_client:
		return None
	
	if image_url and not prompt:
		return None  # prompt is required for imate to video generation
	
	try:
		if image_url:
			image_bytes, mime_type = download_image(image_url)
			if not image_bytes:
				return None
		
			operation = genai_client.models.generate_videos(
				model='veo-2.0-generate-001',
				prompt=prompt,
				image=types.Image(image_bytes=image_bytes, mime_type=mime_type),
				config=types.GenerateVideosConfig(
					number_of_videos=1,
					fps=24,
					duration_seconds=5,
					enhance_prompt=True,
				),
			)
		else:  # generate video from prompt only
			operation = genai_client.models.generate_videos(
				model='veo-2.0-generate-001',
				prompt=prompt,
				config=types.GenerateVideosConfig(
					number_of_videos=1,
					fps=24,
					duration_seconds=5,
					enhance_prompt=True,
				),
			)
		
		time_to_wait = 3 * 60  # 3 minutes
		while not operation.done:
			time.sleep(20)
			operation = genai_client.operations.get(operation)
			time_to_wait -= 20
			if time_to_wait <= 0:
				break
			
		if not operation.done:
			return None
		
		video = operation.result.generated_videos[0].video
		if video and video.video_bytes:
			return upload_resp_file_content_to_bucket(
				resp_file_content=video.video_bytes,
				filename=random_name_generator() + ".mp4",
				content_type="video/mp4"
			)
	
	except Exception as e:
		logger.error(f"Error generating video: {e}")
	
	return None
