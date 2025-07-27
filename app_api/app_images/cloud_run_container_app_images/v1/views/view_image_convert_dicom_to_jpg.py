import os
import logging

import SimpleITK as sitk
from fastapi import APIRouter
from fastapi import File, UploadFile, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
    cleanup_temp_dir, get_temp_file_path,
)


logger = logging.getLogger(__name__)

image_convert_dicom_to_jpg_router = APIRouter(
    tags=["Convert"],
    responses={404: {"description": "Not found"}},
)


@image_convert_dicom_to_jpg_router.post(
    urls.get("convert").get("dicom_to_img"),
    include_in_schema=True,
)
async def convert_dicom_to_jpg(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        token_data: bool = Depends(verify_token),
):
    output_file_path = get_temp_file_path(extension="jpeg")
    temp_dir = os.path.dirname(output_file_path)
    input_dicom_file_path = os.path.join(temp_dir, file.filename)

    try:
        with open(input_dicom_file_path, "wb") as dicom:
            dicom.write(await file.read())

        image = sitk.ReadImage(input_dicom_file_path)

        # Check if the image is 3D and extract a 2D slice if necessary
        if image.GetDimension() > 2:
            # Extract the middle slice of the image
            size = list(image.GetSize())
            index = [0, 0, size[2] // 2]
            size[2] = 0

            extractor = sitk.ExtractImageFilter()
            extractor.SetSize(size)
            extractor.SetIndex(index)
            image = extractor.Execute(image)

        # Optionally, you can rescale the intensity to 0-255
        rescale_filter = sitk.RescaleIntensityImageFilter()
        rescale_filter.SetOutputMinimum(0)
        rescale_filter.SetOutputMaximum(255)
        image = rescale_filter.Execute(image)
        image = sitk.Cast(image, sitk.sitkUInt8)

        # Write the image directly to a JPEG file
        sitk.WriteImage(image, output_file_path)

        background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)
        return FileResponse(
            output_file_path,
            media_type="image/jpeg",
            filename="converted_image.jpeg"
        )
    except (Exception, OSError) as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(file_path=output_file_path)
        raise HTTPException(status_code=500, detail="Server error")
