import os
import logging

import cv2
import numpy as np
from fastapi import APIRouter
from fastapi import HTTPException, Depends, BackgroundTasks, File, UploadFile
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
	get_temp_file_path, cleanup_temp_dir, read_image_from_file_upload
)

logger = logging.getLogger(__name__)

image_cartoonify_router = APIRouter(
	tags=["Image manipulation"],
	responses={404: {"description": "Not found"}},
)


@image_cartoonify_router.post(
	urls.get("image_manipulation").get("cartoonify"),
	include_in_schema=True,
)
async def cartoonify(
		background_tasks: BackgroundTasks,
		file: UploadFile = File(...),
		token_data: bool = Depends(verify_token),
):
	output_file_path = get_temp_file_path(extension="jpeg")
	temp_dir = os.path.dirname(output_file_path)

	image = await read_image_from_file_upload(file)
	image.save(output_file_path)

	try:
		img = cv2.imread(output_file_path)
		for _ in range(3):  # Applying the filter twice for stronger smoothing
			color = cv2.bilateralFilter(img, d=9, sigmaColor=300, sigmaSpace=150)

		# Perform color quantization using k-means clustering
		data = np.float32(color).reshape((-1, 3))
		criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.001)
		k = 8  # Number of color clusters to reduce the image to
		_, labels, centers = cv2.kmeans(
			data, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
		)
		centers = np.uint8(centers)
		quantized = centers[labels.flatten()].reshape(color.shape)

		quantized_hsv = cv2.cvtColor(quantized, cv2.COLOR_BGR2HSV)
		quantized_hsv[..., 2] = cv2.multiply(
			quantized_hsv[..., 2], 1.2
		)  # Increase the brightness of the image
		quantized = cv2.cvtColor(quantized_hsv, cv2.COLOR_HSV2BGR)

		cartoon_file_path = os.path.join(temp_dir, "cartoon.jpeg")

		# Save the cartoon image
		cv2.imwrite(cartoon_file_path, quantized)
		background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)

		return FileResponse(
			cartoon_file_path,
			media_type="image/jpeg",
			filename="cartoon.jpeg",
		)

	except (Exception, OSError) as e:
		cleanup_temp_dir(file_path=output_file_path)
		logging.error(f"Error: {e}")
		raise HTTPException(status_code=500, detail="Server error")
