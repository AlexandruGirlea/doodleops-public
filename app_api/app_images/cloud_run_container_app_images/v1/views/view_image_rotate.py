import logging
from typing import Literal

from PIL import ImageSequence
from fastapi import APIRouter
from fastapi import File, UploadFile, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.constants import FORMAT_MAPPING_FOR_PILLOW
from utils.helper_methods import (
    cleanup_temp_dir, read_image_from_file_upload, get_temp_file_path,
)


logger = logging.getLogger(__name__)

image_rotate_router = APIRouter(
    tags=["General"],
    responses={404: {"description": "Not found"}},
)

NO_PAGES_ERR_MSG = "No pages provided to rotate."
PAGE_NR_ERR_MSG = "Invalid page numbers provided."


@image_rotate_router.post(
    urls.get("general").get("rotate"),
    include_in_schema=True,
)
async def rotate_image(
        background_tasks: BackgroundTasks,
        direction: Literal["right", "left", "upside_down"],
        file: UploadFile = File(...),
        token_data: bool = Depends(verify_token),
):
    image = await read_image_from_file_upload(file)
    extension = file.filename.split('.')[-1]

    output_file_path = get_temp_file_path(extension=extension)
    angle = {
        "right": -90,
        "left": 90,
        "upside_down": 180
    }

    if direction not in angle.keys():
        raise HTTPException(status_code=400, detail="Invalid direction")
    try:

        if file.filename.endswith('.gif'):

            frames = []

            for frame in ImageSequence.Iterator(image):
                frames.append(
                    frame.copy().rotate(angle.get(direction), expand=True)
                )

            frames[0].save(
                output_file_path,
                save_all=True,
                append_images=frames[1:],
                loop=image.info.get('loop', 0),
                duration=image.info.get('duration', 100),
                disposal=image.info.get('disposal', 2),
            )

        else:
            rotated_image = image.rotate(angle.get(direction), expand=True)
            rotated_image.save(
                output_file_path,
                format=FORMAT_MAPPING_FOR_PILLOW.get(extension)
            )

        background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)
        return FileResponse(
            output_file_path,
            media_type=f'application/{extension}',
            filename=f"rotated_{file.filename}"
        )

    except OSError as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(file_path=output_file_path)
        raise HTTPException(status_code=500, detail="Server error")
    except Exception as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(file_path=output_file_path)
        raise HTTPException(status_code=500, detail="Server error")
