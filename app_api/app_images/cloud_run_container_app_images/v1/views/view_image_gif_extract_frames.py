import os
import logging
from typing import Literal

from PIL import ImageSequence
from fastapi import APIRouter
from fastapi import File, UploadFile, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
    cleanup_temp_dir, read_image_from_file_upload,
    get_temp_file_path, archive_to_zip
)


logger = logging.getLogger(__name__)

image_gif_extract_frames_router = APIRouter(
    tags=["GIF"],
    responses={404: {"description": "Not found"}},
)

NO_PAGES_ERR_MSG = "No pages provided to rotate."
PAGE_NR_ERR_MSG = "Invalid page numbers provided."


@image_gif_extract_frames_router.post(
    urls.get("gif").get("extract_frames"),
    include_in_schema=True,
)
async def extract_frames_from_gif(
        background_tasks: BackgroundTasks,
        export_format: Literal["jpeg", "png"] = Query("jpeg"),
        file: UploadFile = File(...),
        token_data: bool = Depends(verify_token),
):
    if not file.filename.lower().endswith(('.gif')):
        raise HTTPException(
            status_code=400,
            detail="Only GIF files are allowed."
        )

    image = await read_image_from_file_upload(file)
    output_file_path = get_temp_file_path(extension=export_format)
    temp_dir = os.path.dirname(output_file_path)

    try:
        index = 1
        for frame in ImageSequence.Iterator(image):
            _frame = frame.copy()
            frame_path = os.path.join(temp_dir, f"frame_{index}.{export_format}")
            if _frame.mode != "RGB":
                _frame = frame.convert("RGB")
            _frame.save(
                frame_path,
                format=export_format.upper()
            )
            del _frame
            index += 1

        archive_to_zip(
            zip_file_path=output_file_path.replace(
                f".{export_format}", ".zip"
            ),
            file_extension=export_format
        )

        background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)
        return FileResponse(
            path=output_file_path.replace(f".{export_format}", ".zip"),
            media_type='application/zip',
            filename="gif_images.zip"
        )

    except OSError as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(file_path=output_file_path)
        raise HTTPException(status_code=500, detail="Server error")
    except Exception as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(file_path=output_file_path)
        raise HTTPException(status_code=500, detail="Server error")
