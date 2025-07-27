import io
import os
import logging
from urllib.parse import unquote

from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter, PageObject
from PIL import Image, ImageEnhance, ImageFont, ImageDraw
from fastapi import APIRouter
from fastapi import File, UploadFile, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
    cleanup_temp_dir, validate_pdf_file_input, get_temp_pdf_path,
    get_random_file_name, resize_image
)


logger = logging.getLogger("APP_PDF_V1_"+__name__)

pdf_watermark_router = APIRouter(
    tags=["PDF Watermark API"],
    responses={404: {"description": "Not found"}},
)

MAX_TEXT_LENGTH = 25


@pdf_watermark_router.post(
    urls.get("view_pdf_watermark").get("text"),
    include_in_schema=True,
)
async def watermark_text(
        background_tasks: BackgroundTasks,
        text: str = Query(
            ..., title="Text to watermark", max_length=MAX_TEXT_LENGTH
        ),
        transparency: float = Query(0.5, title="Opacity", ge=0, le=1),
        grid_rows: int = Query(
            1, title="Number of rows in the watermark grid", ge=1, le=3
        ),
        grid_columns: int = Query(
            1, title="Number of columns in the watermark grid", ge=1, le=3
        ),
        rgb_text_color: str = Query(
            "255,255,255", title="RGB text color",
            ription="RGB color for the text in the format '255,255,255'"
        ),
        rotation_angle: int = Query(0, ge=-360, le=360),
        file: UploadFile = File(...),
        token_data: bool = Depends(verify_token),
) -> FileResponse:
    text = unquote(text)
    if len(text) > MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Text length exceeds the maximum limit of {MAX_TEXT_LENGTH}"
        )
    if rgb_text_color:
        colors = [
            int(color) for color in rgb_text_color.split(",")
            if color.isdigit() and 0 <= int(color) <= 255
        ]
        if len(colors) != 3:
            raise HTTPException(
                status_code=400,
                detail="RGB color values must be between 0 and 255"
            )
    else:
        colors = [255, 255, 255]
    r, g, b = colors

    validate_pdf_file_input(file)
    pdf_path = get_temp_pdf_path()
    temp_dir = os.path.dirname(pdf_path)
    random_name = get_random_file_name()

    watermark_path = os.path.join(temp_dir, f"{random_name}_watermark.pdf")
    out_file_path = os.path.join(temp_dir, f"{random_name}.pdf")
    try:

        # Read the PDF to get the first page size
        with open(pdf_path, "wb") as f:
            f.write(await file.read())

        pdf_reader = PdfReader(pdf_path)
        first_page = pdf_reader.pages[0]
        page_width = first_page.mediabox[2]
        page_height = first_page.mediabox[3]

        # Create a watermark PDF with dimensions matching the first page
        c = canvas.Canvas(watermark_path, pagesize=(page_width, page_height))
        text_width = page_width / grid_columns
        text_height = page_height / grid_rows
        font_size = min(text_width, text_height) / (len(text) * 0.6)

        c.setFont("Helvetica", font_size)
        c.setFillColorRGB(r / 255.0, g / 255.0, b / 255.0, alpha=transparency)

        for row in range(grid_rows):
            for col in range(grid_columns):
                x = col * text_width + text_width / 2
                y = page_height - (row * text_height + text_height / 2)
                c.saveState()
                c.translate(x, y)
                c.rotate(rotation_angle)
                c.drawCentredString(0, 0, text)
                c.restoreState()

        c.save()

        # Overlay the watermark PDF on each page of the original PDF
        watermark_reader = PdfReader(watermark_path)
        watermark_page = watermark_reader.pages[0]

        pdf_writer = PdfWriter()

        for page in pdf_reader.pages:
            page.merge_page(watermark_page)
            pdf_writer.add_page(page)

        with open(out_file_path, 'wb') as out_file:
            pdf_writer.write(out_file)

        background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)
        return FileResponse(
            out_file_path, media_type='application/pdf', filename='output.pdf'
        )

    except OSError as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(temp_dir=temp_dir)
        raise HTTPException(status_code=500, detail="Server error")
    except Exception as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(temp_dir=temp_dir)
        raise HTTPException(status_code=500, detail="Server error")


@pdf_watermark_router.post(
    urls.get("view_pdf_watermark").get("image"),
    include_in_schema=True,
)
async def watermark_image(
        background_tasks: BackgroundTasks,
        grid_rows: int = Query(1, title="Number of rows in the watermark grid",
                               ge=1, le=3),
        grid_columns: int = Query(1, title="Number of columns in the watermark "
                                           "grid", ge=1, le=3),
        pdf_file: UploadFile = File(
            ..., description="The PDF file to add the watermark to"
            ),
        image_scale: float = Query(
            0.17, title="Scale factor", ge=0.05, le=1,
            description="Scale factor for the image, between 0.05 and 1"
        ),
        transparency: float = Query(0.5, ge=0, le=1),
        image_file: UploadFile = File(
            ..., description="The image to use as watermark (PNG, JPG, SVG)"
        ),
        token_data: bool = Depends(verify_token),
) -> FileResponse:
    validate_pdf_file_input(pdf_file)

    image_ext = image_file.filename.split('.')[-1].lower()

    if image_ext not in ("jpg", "jpeg", "png", "svg"):
        raise HTTPException(
            status_code=400, detail="Invalid image format. Only PNG, JPG, SVG "
                                    "formats are supported"
        )

    try:
        image_data = await image_file.read()
        if image_ext in ("jpg", "jpeg", "png"):
            image = Image.open(io.BytesIO(image_data)).convert("RGBA")
        else:
            import cairosvg
            image = Image.open(
                io.BytesIO(cairosvg.svg2png(bytestring=image_data))
            ).convert("RGBA")

        alpha = image.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(transparency)
        image.putalpha(alpha)

    except Exception as e:
        logging.error(f"Error: {e}")
        raise HTTPException(
            status_code=400, detail="Invalid image format. Only PNG, JPG, SVG "
                                    "formats are supported"
        )

    pdf_path = get_temp_pdf_path()
    temp_dir = os.path.dirname(pdf_path)
    random_name = get_random_file_name()
    watermark_path = os.path.join(temp_dir, f"{random_name}_watermark.pdf")
    out_file_path = os.path.join(temp_dir, f"{random_name}.pdf")

    image = resize_image(image, 300)
    image_temp_path = os.path.join(temp_dir, f"{random_name}.png")
    image.save(image_temp_path, 'PNG')

    try:
        # Read the PDF to get the first page size
        with open(pdf_path, "wb") as f:
            f.write(await pdf_file.read())

        pdf_reader = PdfReader(pdf_path)
        first_page = pdf_reader.pages[0]
        page_width = first_page.mediabox[2]
        page_height = first_page.mediabox[3]

        image_width = page_width / grid_columns
        image_height = page_height / grid_rows

        # Create a watermark PDF that will hold the image
        c = canvas.Canvas(watermark_path, pagesize=(page_width, page_height))

        for row in range(grid_rows):
            for col in range(grid_columns):
                x = col * image_width
                y = page_height - (row + 1) * image_height

                scaled_width = image_width * image_scale
                scaled_height = image_height * image_scale

                # Adjust x and y to center the scaled image
                x_centered = x + (image_width - scaled_width) / 2
                y_centered = y + (image_height - scaled_height) / 2

                c.drawImage(image_temp_path, x_centered, y_centered,
                            width=scaled_width, height=scaled_height,
                            mask='auto', preserveAspectRatio=True)
        c.save()

        watermark_reader = PdfReader(watermark_path)
        watermark_page = watermark_reader.pages[0]

        pdf_writer = PdfWriter()

        for page in pdf_reader.pages:
            page.merge_page(watermark_page)
            pdf_writer.add_page(page)

        with open(out_file_path, 'wb') as out_file:
            pdf_writer.write(out_file)

        background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)
        return FileResponse(
            out_file_path, media_type='application/pdf', filename='output.pdf'
        )

    except OSError as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(temp_dir=temp_dir)
        raise HTTPException(status_code=500, detail="Server error")
    except Exception as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(temp_dir=temp_dir)
        raise HTTPException(status_code=500, detail="Server error")
