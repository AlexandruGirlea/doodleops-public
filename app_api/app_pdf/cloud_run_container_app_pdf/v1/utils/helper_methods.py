import os
import uuid
import shutil
import logging
import zipfile
from typing import Optional

import pandas as pd
from PIL import Image
from fastapi import UploadFile, HTTPException

logger = logging.getLogger("APP_PDF_V1_"+__name__)


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
    if not temp_dir and file_path and file_path.endswith('.pdf'):
        temp_dir = os.path.dirname(file_path)
    shutil.rmtree(temp_dir)


def validate_pdf_file_input(file: UploadFile) -> bool:
    filename = file.filename
    if not file.filename or not filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid file name")

    elif file.content_type != 'application/pdf':
        raise HTTPException(status_code=400, detail="Unsupported file type")

    return True


def validate_image_file_input(
        file: UploadFile,
        image_file_extensions: tuple[str] = ('jpeg', 'jpg', 'png')
) -> str:
    """Returns file format"""
    if file.filename == '':
        raise HTTPException(status_code=400, detail="No selected file")

    elif not file.filename.split('.')[-1].lower() in image_file_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    elif not file.content_type.startswith("image"):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    return file.filename.split('.')[-1]


def get_temp_pdf_path() -> str:
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
    pdf_path = os.path.join(temp_dir, f'{file_name}.pdf')
    return pdf_path


def resize_image(image: Image, max_size: int) -> Image:
    if max(image.size) > max_size:
        ratio = max_size / float(max(image.size))
        new_size = tuple([int(x * ratio) for x in image.size])
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    return image


def convert_pandas_to_excel(
        df_tables: list[pd.DataFrame], excel_path: str,
        multiple_files: bool = False
) -> bool:
    if not all(isinstance(df, pd.DataFrame) for df in df_tables):
        raise HTTPException(
            status_code=500, detail="Invalid table data type"
        )

    if len(df_tables) == 1 or not multiple_files:
        with pd.ExcelWriter(excel_path) as writer:
            for table_number, df_table in enumerate(df_tables):
                df_table.to_excel(
                    writer, sheet_name=f'table_{table_number}', index=False
                )

        return True

    else:
        path_dir = os.path.dirname(excel_path)
        excel_path = os.path.join(path_dir, 'table_{table_number}.xlsx')
        for table_number, df_table in enumerate(df_tables):

            with pd.ExcelWriter(
                    excel_path.format(table_number=table_number)
            ) as writer:
                df_table.to_excel(
                    writer, sheet_name=f'table_{table_number}', index=False
                )
        return True


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
