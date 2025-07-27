import io
import os
import uuid
import json
import shutil
import logging
import zipfile
import base64
from io import BytesIO
import xml.etree.ElementTree as ET
from typing import Optional, Literal, Union

from PIL import Image
from fastapi import UploadFile, HTTPException
from utils.constants import IMAGE_FILE_EXTENSIONS

logger = logging.getLogger(__name__)


def get_random_file_name():
    return uuid.uuid4().hex


def get_unique_temp_dir():
    return f'/tmp/{uuid.uuid4().hex}'


def cleanup_temp_dir(
        file_path: Optional[str] = None, temp_dir: Optional[str] = None
) -> None:
    """Function to clean up the temporary directory."""
    if not temp_dir and not file_path:
        return
    if file_path and not temp_dir:
        temp_dir = os.path.dirname(file_path)
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    else:
        logging.error(f"Temporary directory not found: {temp_dir}")
    return


def validate_image_file_input(file: UploadFile) -> str:
    """Returns file format"""
    if file.filename == '':
        raise HTTPException(status_code=400, detail="No selected file")

    file_name_array = file.filename.split('.')

    if (
            len(file_name_array) < 2 or
            file_name_array[-1].lower() not in IMAGE_FILE_EXTENSIONS
    ):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    elif file.content_type not in {
        f"image/{e.replace('.', '')}" for e in IMAGE_FILE_EXTENSIONS
    }:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    return file.filename.split('.')[-1]


def get_temp_file_path(extension: str = "jpeg") -> str:
    try:
        temp_dir = get_unique_temp_dir()
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=False)
        else:
            logging.error(f"Temporary directory already exists, {temp_dir}")
            raise HTTPException(
                status_code=500, detail="Server error")
    except OSError as e:
        logging.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Server error")

    file_name = get_random_file_name()
    return os.path.join(temp_dir, f'{file_name}.{extension}')


def resize_image(image: Image, max_size: int) -> Image:
    if max(image.size) > max_size:
        ratio = max_size / float(max(image.size))
        new_size = tuple([int(x * ratio) for x in image.size])
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    return image


def archive_to_zip(
        zip_file_path: str,
        file_extension: str = None
) -> None:
    dir_path = os.path.dirname(zip_file_path)
    with zipfile.ZipFile(zip_file_path, 'w') as zipf:
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith(file_extension):
                    zipf.write(os.path.join(root, file), file)
    return


async def read_image_from_file_upload(file: UploadFile) -> Image:
    validate_image_file_input(file)

    try:
        image = Image.open(io.BytesIO(await file.read()))
        # OBS: do not do any convert here because it will break the image
    except Exception as e:
        logging.error(f"Error: {e}")
        raise HTTPException(status_code=400, detail="Could not read image")

    return image


def get_iso_639_2_languages(
        resp_type: Literal["dict", "list"] = "list"
) -> Optional[Union[dict, list]]:
    with open('utils/iso_639-languages.json') as f:
        iso_639_1_languages = json.load(f)

    if resp_type == "dict":
        return iso_639_1_languages

    iso_639_2_languages = {}
    for value in iso_639_1_languages.values():
        iso_639_2_languages[value['639-2']] = value['name']

    return iso_639_2_languages


def parse_svg_dimensions(svg_path) -> tuple[int, int]:
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        width = root.get('width')
        height = root.get('height')
        viewBox = root.get('viewBox')

        if viewBox:
            _, _, width, height = viewBox.split()

        if width and height:
            width = int(float(width))
            height = int(float(height))
        else:
            width = height = 400  # default size

        return width, height

    except Exception as e:
        logging.error(f"Error: {e}")
        raise HTTPException(
            status_code=400, detail="Could not read SVG dimensions"
        )


def overlay_png_on_svg(
        svg_path: str,
        png_file_content: Image,
        output_path: str
) -> str:
    # Read and parse the SVG file
    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Attempt to find the viewBox attribute to adjust dimensions
    view_box = root.get('viewBox')
    if view_box:
        parts = view_box.split()
        width = int(parts[2])
        height = int(parts[3])
    else:
        width, height = root.attrib.get('width'), root.attrib.get('height')
        width, height = int(width), int(height)

    # Convert PIL Image to PNG bytes
    png_buffer = BytesIO()
    png_file_content.save(png_buffer, format="PNG")
    encoded_string = base64.b64encode(png_buffer.getvalue()).decode('utf-8')

    # Calculate dimensions for the PNG
    basewidth = width // 5  # 20% of the width
    wpercent = basewidth / float(png_file_content.size[0])
    hsize = int((float(png_file_content.size[1]) * wpercent))
    png_width = basewidth
    png_height = hsize

    # Calculate the center position
    insert_x = (width - png_width) // 2
    insert_y = (height - png_height) // 2

    # Create a new <image> element
    new_image = ET.Element('{http://www.w3.org/2000/svg}image', {
        '{http://www.w3.org/1999/xlink}href': (
            f"data:image/png;base64,{encoded_string}"
        ),
        'x': str(insert_x),
        'y': str(insert_y),
        'width': str(png_width),
        'height': str(png_height)
    })
    root.append(new_image)

    # Save the modified SVG
    tree.write(output_path)

    return output_path
