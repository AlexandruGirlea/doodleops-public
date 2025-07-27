import os
import zipfile
import logging

from fastapi import APIRouter
from fastapi import File, UploadFile, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from pypdf import PdfReader
from pdf2image import convert_from_path

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
    cleanup_temp_dir, validate_pdf_file_input, get_temp_pdf_path,
)


logger = logging.getLogger("APP_PDF_V1_"+__name__)
MAX_PAGES = 100

pdf_convert_format_to_image_router = APIRouter(
    tags=["PDF Convert Format API to Image"],
    responses={404: {"description": "Not found"}},
)


@pdf_convert_format_to_image_router.post(
    urls.get("view_pdf_convert_to_image"),
    include_in_schema=True,
)
async def pdf_to_image(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        token_data: bool = Depends(verify_token),
):
    validate_pdf_file_input(file)
    pdf_path = get_temp_pdf_path()
    temp_dir = os.path.dirname(pdf_path)
    random_name = "pdf_to_image"
    try:
        with open(pdf_path, "wb") as f:
            f.write(await file.read())

        # check if the pdf has more than 100 pages do not use convert_from_path
        reader = PdfReader(pdf_path)
        number_of_pages = len(reader.pages)

        if number_of_pages > MAX_PAGES:
            del reader
            raise HTTPException(
                status_code=400,
                detail=(
                    f"PDF has more than {MAX_PAGES} pages. Please use the "
                    f"delete service to remove some pages."
                ),
            )
        del reader

        # Convert PDF to images
        images = convert_from_path(pdf_path)

        if len(images) == 1:  # return single image
            image_path = os.path.join(temp_dir, f'{random_name}.jpeg')
            images[0].save(image_path, 'JPEG')
            background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)
            return FileResponse(
                image_path, media_type='image/jpeg', filename='image.jpeg'
            )

        zip_path = os.path.join(temp_dir, f'{random_name}.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for i, image in enumerate(images):
                image_path = os.path.join(temp_dir, f'{random_name}_{i + 1}.jpeg')
                image.save(image_path, 'JPEG')
                zipf.write(image_path, os.path.basename(image_path))
        background_tasks.add_task(
            cleanup_temp_dir, temp_dir=temp_dir
        )
        return FileResponse(
            zip_path, media_type='application/zip', filename='images.zip'
        )
    except HTTPException as e:
        cleanup_temp_dir(temp_dir=temp_dir)
        raise e

    except OSError as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(temp_dir=temp_dir)
        raise HTTPException(status_code=500, detail="Server error")
    except Exception as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(temp_dir=temp_dir)
        raise HTTPException(status_code=500, detail="Server error")
