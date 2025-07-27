import logging

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

image_crop_router = APIRouter(
    tags=["General"],
    responses={404: {"description": "Not found"}},
)


@image_crop_router.post(
    urls.get("general").get("crop"),
    include_in_schema=True,
)
async def crop_image(
        background_tasks: BackgroundTasks,
        crop_box: str = Query(
            ...,
            description="Format: `x1,y1,x2,y2` (left, upper, right, lower)"
        ),
        file: UploadFile = File(...),
        token_data: bool = Depends(verify_token),
):
    image = await read_image_from_file_upload(file)
    extension = file.filename.split('.')[-1]

    if not crop_box.replace(',', '').isdigit() or len(crop_box.split(',')) != 4:
        raise HTTPException(status_code=400, detail="Invalid crop box format")

    # check if crop box is inside the image
    x1, y1, x2, y2 = [int(i) for i in crop_box.split(',')]
    width, height = image.size
    if x1 < 0 or y1 < 0 or x2 > width or y2 > height or x1 >= x2 or y1 >= y2:
        raise HTTPException(status_code=400, detail="Invalid crop box")

    output_file_path = get_temp_file_path(extension)
    try:

        if file.filename.lower().endswith('.gif'):

            frames = []

            for frame in ImageSequence.Iterator(image):
                frames.append(
                    frame.crop((x1, y1, x2, y2))
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
            cropped_img = image.crop((x1, y1, x2, y2))
            cropped_img.save(
                output_file_path,
                format=FORMAT_MAPPING_FOR_PILLOW.get(extension)
            )

        background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)

        return FileResponse(
            output_file_path,
            media_type=f'image/{extension}',
            filename=f"cropped.{extension}",
        )

    except OSError as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(file_path=output_file_path)
        raise HTTPException(status_code=500, detail="Server error")
    except Exception as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(file_path=output_file_path)
        raise HTTPException(status_code=500, detail="Server error")
