import os
import logging

import cv2
import numpy as np
from skimage.metrics import structural_similarity
from fastapi import APIRouter
from fastapi import (
    Form, File, UploadFile, HTTPException, BackgroundTasks, Depends, Form
)
from fastapi.responses import FileResponse, Response

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
    cleanup_temp_dir, read_image_from_file_upload, get_temp_file_path
)


logger = logging.getLogger(__name__)

image_compare_images_router = APIRouter(
    tags=["General"],
    responses={404: {"description": "Not found"}},
)

NO_PAGES_ERR_MSG = "No pages provided to rotate."
PAGE_NR_ERR_MSG = "Invalid page numbers provided."
HIGH_SIMILARITY_THRESHOLD = 0.80  # 80%
LOW_SIMILARITY_THRESHOLD = 0.50   # 30%


@image_compare_images_router.post(
    urls.get("general").get("compare_images"),
    include_in_schema=True,
)
async def compare_images(
        background_tasks: BackgroundTasks,
        img_1: UploadFile = File(...),
        img_2: UploadFile = File(...),
        contour_color: tuple[int, int, int] = Form((0, 255, 0)),
        token_data: bool = Depends(verify_token),
):
    """
    Compare two images by aligning them based on prominent features and
     highlighting the differences or similarities.
    """
    output_file_path = get_temp_file_path(extension="png")
    temp_dir = os.path.dirname(output_file_path)

    img_1_path = os.path.join(temp_dir, 'img_1.png')
    img_2_path = os.path.join(temp_dir, 'img_2.png')

    # Validate file extensions
    if not all(
            file.filename.lower().endswith(('.jpeg', '.jpg', '.png')) for file in
            (img_1, img_2)
    ):
        raise HTTPException(
            status_code=400,
            detail="Only JPEG or PNG files are allowed."
        )

    # Save uploaded images to temporary paths
    img_1_image = await read_image_from_file_upload(img_1)
    img_1_image = img_1_image.convert('RGB')
    img_1_image.save(img_1_path)

    img_2_image = await read_image_from_file_upload(img_2)
    img_2_image = img_2_image.convert('RGB')
    img_2_image.save(img_2_path)

    try:
        # Read images using OpenCV
        img1 = cv2.imread(img_1_path)
        img2 = cv2.imread(img_2_path)

        if img1 is None or img2 is None:
            raise HTTPException(
                status_code=400,
                detail="Failed to read one of the images."
            )

        # Convert images to grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        # Initialize ORB detector
        orb = cv2.ORB_create(5000)

        # Detect keypoints and descriptors
        keypoints1, descriptors1 = orb.detectAndCompute(gray1, None)
        keypoints2, descriptors2 = orb.detectAndCompute(gray2, None)

        if descriptors1 is None or descriptors2 is None:
            raise HTTPException(
                status_code=400,
                detail="Could not find descriptors in one of the images."
            )

        # Initialize BFMatcher
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

        # Match descriptors
        matches = bf.match(descriptors1, descriptors2)

        # Sort matches by distance (best matches first)
        matches = sorted(matches, key=lambda x: x.distance)

        # Select top matches (you can adjust the number as needed)
        num_good_matches = int(len(matches) * 0.15)
        good_matches = matches[:num_good_matches]

        if len(good_matches) < 4:
            raise HTTPException(
                status_code=400,
                detail="Not enough good matches to compute alignment."
            )

        # Extract location of good matches
        src_pts = np.float32(
            [keypoints1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32(
            [keypoints2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        # Compute homography using RANSAC
        homography, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

        if homography is None:
            raise HTTPException(
                status_code=400,
                detail="Could not compute homography between images."
            )

        # Warp img1 to align with img2
        height, width, channels = img2.shape
        aligned_img1 = cv2.warpPerspective(img1, homography, (width, height))

        # Convert aligned image to grayscale
        aligned_gray1 = cv2.cvtColor(aligned_img1, cv2.COLOR_BGR2GRAY)

        # Compute structural similarity between aligned images
        score, diff = structural_similarity(aligned_gray1, gray2, full=True)

        # Scale the difference image to the range [0, 255] and convert to uint8
        diff = (diff * 255).astype("uint8")

        # Apply a threshold to get binary image of differences
        threshold_value = 10  # Adjust based on experimentation

        # Highlight differences: areas where diff is low (more different)
        thresh = cv2.threshold(
            diff, threshold_value, 255, cv2.THRESH_BINARY_INV
        )[1]

        # Apply morphological operations to remove small noise and enhance regions
        kernel = np.ones((5, 5), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_DILATE, kernel, iterations=1)

        # Find contours of the highlighted areas
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)

        # Create a mask to draw contours
        mask_diff = np.zeros_like(img2)

        # Calculate minimum area threshold
        image_area = img2.shape[0] * img2.shape[1]
        min_area = max(int(image_area * 0.001),
                       10)  # 0.1% of image area or 10 pixels

        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= min_area:
                # Draw contour on the mask
                cv2.drawContours(
                    mask_diff, [contour], -1, (0, 0, 255), thickness=cv2.FILLED
                )

        # Convert mask_diff to single channel for masking
        mask_gray = cv2.cvtColor(mask_diff, cv2.COLOR_BGR2GRAY)

        # Create boolean mask where differences are detected
        mask_boolean = mask_gray == 255

        # Assign red color to the differences in the highlighted_image
        highlighted_image = img2.copy()
        highlighted_image[mask_boolean] = (0, 0, 255)  # Red color for differences

        # Optionally, create an outline around differences
        contours, _ = cv2.findContours(
            mask_gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return Response(content="No differences found between images.")

        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= min_area:
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(
                    highlighted_image,
                    (x, y),
                    (x + w, y + h),
                    contour_color,
                    2
                )

        # Save the highlighted image
        cv2.imwrite(output_file_path, highlighted_image)

        # Schedule cleanup of temporary files
        background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)

        return FileResponse(
            output_file_path,
            media_type='image/png',
            filename="highlighted_image.png"
        )

    except HTTPException as he:
        raise he
    except OSError as e:
        logging.error(f"OS Error: {e}")
        cleanup_temp_dir(file_path=output_file_path)
        raise HTTPException(status_code=500,
                            detail="Server error while processing images.")
    except Exception as e:
        logging.error(f"Unexpected Error: {e}")
        cleanup_temp_dir(file_path=output_file_path)
        raise HTTPException(status_code=500,
                            detail="An unexpected server error occurred.")
