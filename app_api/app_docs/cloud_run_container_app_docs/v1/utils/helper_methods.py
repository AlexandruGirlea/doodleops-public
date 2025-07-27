import os
import uuid
import shutil
import logging
import zipfile
from typing import Optional

from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

EXCEL_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


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


def get_temp_file_path(extension: str) -> str:
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


def archive_to_zip(
        temp_dir_path: str,
        zip_file_name: str = "archive.zip",
        file_ends_with: str = None,
        file_starts_with: str = None,
) -> str:
    if not os.path.isdir(temp_dir_path):
        logging.error(f"Temporary directory not found: {temp_dir_path}")
        raise HTTPException(status_code=500, detail="Server error")

    if not file_starts_with and not file_ends_with:
        logging.error(
            "Either file_starts_with or file_ends_with must be provided"
        )
        HTTPException(status_code=500, detail="Server error")

    if not zip_file_name.endswith('.zip'):
        zip_file_name = f"{zip_file_name}.zip"

    zip_file_path = os.path.join(temp_dir_path, zip_file_name)

    with (zipfile.ZipFile(zip_file_path, 'w') as zipf):
        for root, _, files in os.walk(temp_dir_path):
            for file in files:

                if file_starts_with and not file.startswith(file_starts_with):
                    continue

                if file_ends_with and not file.endswith(file_ends_with):
                    continue

                zipf.write(os.path.join(root, file), file)

    return zip_file_path


def validate_doc_file_input(
        file: UploadFile,
        file_extensions: tuple
) -> str:
    """Returns file format"""
    if file.filename == '':
        raise HTTPException(status_code=400, detail="No selected file")

    elif not file.filename.split('.')[-1] in file_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    return file.filename.split('.')[-1]


def excel_column_to_index(col_str):
    """
    Convert an Excel column letter (e.g., 'A', 'AB') into a zero-based column
    index.
    """
    # Ensure the column string is uppercase for uniform processing
    col_str = col_str.upper()

    # Validate input: only letters and within Excel's column range
    if not col_str.isalpha():
        raise HTTPException(
            status_code=400,
            detail="Column string must consist of letters only."
        )

    # Check if column is within Excel's limits (up to "XFD")
    if len(col_str) > 3 or (len(col_str) == 3 and col_str > 'XFD'):
        raise HTTPException(
            status_code=400,
            detail="Column string out of Excel's limits (A to XFD)."
        )

    expn = 0
    col_index = 0
    for char in reversed(col_str):
        col_index += (ord(char) - ord('A') + 1) * (26 ** expn)
        expn += 1

    return col_index - 1
