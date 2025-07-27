import os
import logging

from pypdf import PdfReader, PdfWriter
from fastapi import(
    File, UploadFile, HTTPException, BackgroundTasks, Depends, Query, APIRouter
)
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
    cleanup_temp_dir, validate_pdf_file_input, get_temp_pdf_path,
    get_random_file_name
)
from schemas.view_pdf_rotate import InputPDFRotate


logger = logging.getLogger("APP_PDF_V1_"+__name__)

pdf_rotate_pages_router = APIRouter(
    tags=["PDF Rotate Pages"],
    responses={404: {"description": "Not found"}},
)

NO_PAGES_ERR_MSG = "No pages provided to rotate."
PAGE_NR_ERR_MSG = "Invalid page numbers provided."
GENERAL_ERR_MSG = (
        "Could not rotate pages. If the problem persists, please contact support."
)


@pdf_rotate_pages_router.post(
    urls.get("view_pdf_rotate"),
    include_in_schema=True,
)
async def rotate_pages(
        background_tasks: BackgroundTasks,
        pages_to_rotate_left: str = Query(
            None, title="Comma separated page numbers to rotate left"
        ),
        pages_to_rotate_right: str = Query(
            None, title="Comma separated page numbers to rotate right"
        ),
        pages_to_rotate_upside_down: str = Query(
            None, title="Comma separated page numbers to rotate upside down"
        ),
        file: UploadFile = File(...),
        token_data: bool = Depends(verify_token),
):

    try:
        clean_input = InputPDFRotate(  # converted to clean input
            pages_to_rotate_right=pages_to_rotate_right,
            pages_to_rotate_left=pages_to_rotate_left,
            pages_to_rotate_upside_down=pages_to_rotate_upside_down,
        )
    except ValueError as e:
        logging.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=GENERAL_ERR_MSG)

    pages_to_rotate_left = clean_input.pages_to_rotate_left
    pages_to_rotate_right = clean_input.pages_to_rotate_right
    pages_to_rotate_upside_down = clean_input.pages_to_rotate_upside_down

    if not any(
            (pages_to_rotate_left, pages_to_rotate_right,
            pages_to_rotate_upside_down)
    ):
        raise HTTPException(status_code=400, detail=NO_PAGES_ERR_MSG)

    if (
            set(pages_to_rotate_left) & set(pages_to_rotate_right) or
            set(pages_to_rotate_left) & set(pages_to_rotate_upside_down) or
            set(pages_to_rotate_right) & set(pages_to_rotate_upside_down)
    ):
        raise HTTPException(status_code=400, detail="Pages to rotate overlap.")

    validate_pdf_file_input(file)
    right_angle, left_angle, upside_down_angle = 90, -90, 180

    pdf_path = get_temp_pdf_path()
    temp_dir = os.path.dirname(pdf_path)
    random_name = get_random_file_name()
    rotated_pdf = os.path.join(temp_dir, f"{random_name}.pdf")

    try:
        with open(pdf_path, "wb") as f:
            f.write(await file.read())

        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        num_pages = len(reader.pages)

        for i in range(num_pages):
            page = reader.pages[i]
            if i in pages_to_rotate_right:
                # Rotate page by angle
                page.rotate(right_angle)
            elif i in pages_to_rotate_left:
                # Rotate page by angle
                page.rotate(left_angle)
            elif i in pages_to_rotate_upside_down:
                # Rotate page by angle
                page.rotate(upside_down_angle)
            writer.add_page(page)

        with open(rotated_pdf, "wb") as f_out:
            writer.write(f_out)

        background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)
        return FileResponse(
            rotated_pdf, media_type='application/pdf', filename='rotated.pdf'
        )

    except ValueError as e:
        if str(e) == PAGE_NR_ERR_MSG:
            raise HTTPException(status_code=400, detail=PAGE_NR_ERR_MSG)
        logging.error(f"Error: {e}")
        cleanup_temp_dir(temp_dir=temp_dir)
        raise HTTPException(status_code=400, detail="Bad request")

    except OSError as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(temp_dir=temp_dir)
        raise HTTPException(status_code=500, detail="Server error")
    except Exception as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(temp_dir=temp_dir)
        raise HTTPException(status_code=500, detail="Server error")
