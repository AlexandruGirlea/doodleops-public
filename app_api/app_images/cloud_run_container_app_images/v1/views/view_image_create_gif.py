import logging
from typing import List

from fastapi import APIRouter
from fastapi import (
    File, UploadFile, HTTPException, BackgroundTasks, Depends, Query
)
from fastapi.responses import FileResponse
from moviepy.editor import VideoFileClip
from PIL import Image

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
    cleanup_temp_dir, read_image_from_file_upload,
    get_temp_file_path,
)


logger = logging.getLogger(__name__)

image_create_gif_router = APIRouter(
    tags=["GIF"],
    responses={404: {"description": "Not found"}},
)

NO_PAGES_ERR_MSG = "No pages provided to rotate."
PAGE_NR_ERR_MSG = "Invalid page numbers provided."


@image_create_gif_router.post(
    urls.get("gif").get("create"),
    include_in_schema=True,
)
async def create_gif(
        background_tasks: BackgroundTasks,
        loop: int = Query(
            0, ge=0, le=100, description="Number of loops for the GIF"
        ),
        duration: int = Query(
            200, ge=50, le=1000,
            description="Duration of each frame in milliseconds"
        ),
        img_files: List[UploadFile] = File(None),
        movie_file: UploadFile = File(None),
        token_data: bool = Depends(verify_token),
):
    if not img_files and not movie_file:
        raise HTTPException(status_code=400, detail="No files provided")

    if movie_file and img_files:
        raise HTTPException(
            status_code=400,
            detail="Either provide multiple images or a movie file"
        )

    output_file_path = get_temp_file_path(extension="gif")

    if img_files and not all(
                file.filename.lower().endswith(('.jpeg', '.jpg', '.png'))
                for file in img_files
    ):
        raise HTTPException(
            status_code=400,
            detail="Only JPEG or PNG files are allowed."
        )

    elif (
            movie_file and
            not movie_file.filename.lower().endswith(('.mp4', '.avi', '.mov'))
    ):
        raise HTTPException(
            status_code=400,
            detail="Only MP4, AVI, and MOV files are allowed."
        )

    try:
        converted_images = None
        if img_files:
            images = []
            first_image = None
            width = height = None

            for file in img_files:
                image = await read_image_from_file_upload(file)
                if not first_image:
                    first_image = image
                    width, height = first_image.size
                    images.append(first_image.convert('RGBA'))
                else:
                    resized_image = image.resize((width, height))
                    images.append(resized_image.convert('RGBA'))

            converted_images = [img.convert('P') for img in images]

        elif movie_file:
            file_extension = movie_file.filename.split('.')[-1].lower()
            input_movie_file_path = get_temp_file_path(extension=file_extension)

            with open(input_movie_file_path, 'wb') as f:
                f.write(await movie_file.read())

            clip = VideoFileClip(input_movie_file_path)

            rotation = getattr(clip, 'rotation', 0)
            rotation = rotation if rotation in (0, 90, 180, 270) else 0

            duration_sec = clip.duration  # Duration in seconds

            if duration_sec <= 0:
                raise HTTPException(status_code=400,
                                    detail="Invalid video duration")

            max_frames = 40
            num_frames = min(max_frames, int(duration_sec * clip.fps))
            if num_frames < 1:
                num_frames = 1

            # Generate time points for frame extraction
            times = [t * duration_sec / (num_frames - 1) for t in
                     range(num_frames)]

            frames = []
            for t in times:
                frame = clip.get_frame(t)
                image = Image.fromarray(frame)
                frames.append(image)

            clip.close()
            del clip

            original_size = frames[0].size
            if original_size and rotation in [90, 270]:
                # Swap width and height for 90 or 270 degrees rotation
                original_size = (original_size[1], original_size[0])

            converted_images = [
                img.resize(original_size, Image.Resampling.LANCZOS).convert(
                    'RGB'
                ).convert('P', palette=Image.Resampling.LANCZOS)
                for img in frames
            ]
        if converted_images:
            converted_images[0].save(
                output_file_path, format='GIF', save_all=True,
                append_images=converted_images[1:],
                loop=loop, duration=duration, disposal=2, optimize=True
            )

        background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)
        if movie_file:
            background_tasks.add_task(
                cleanup_temp_dir, file_path=input_movie_file_path
            )
        return FileResponse(
            output_file_path,
            media_type='application/gif',
            filename="your_gif.gif"
        )

    except OSError as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(file_path=output_file_path)
        raise HTTPException(status_code=500, detail="Server error")
    except Exception as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(file_path=output_file_path)
        raise HTTPException(status_code=500, detail="Server error")
