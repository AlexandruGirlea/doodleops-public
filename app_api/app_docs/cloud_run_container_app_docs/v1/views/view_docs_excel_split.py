import os
import logging
from typing import Literal
from urllib.parse import unquote

import aiofiles
import pandas as pd
from fastapi import APIRouter
from fastapi import (
    File, UploadFile, HTTPException, BackgroundTasks, Depends, Query
)
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
    cleanup_temp_dir, get_temp_file_path, archive_to_zip, validate_doc_file_input
)
from utils.view_docs_excel_split import MAX_FILE_SPLIT, MAX_FILE_SPLIT_ERROR


logger = logging.getLogger(__name__)

docs_excel_split_router = APIRouter(
    tags=["Excel"],
    responses={404: {"description": "Not found"}},
)


@docs_excel_split_router.post(
    urls.get("excel").get("split"),
    include_in_schema=True,
)
async def excel_split(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        row_count: int = Query(1, ge=1),
        sheet_name: str = Query(None, min_length=1, max_length=31),
        output_format: Literal['xlsx', 'csv'] = Query('xlsx'),
        token_data: bool = Depends(verify_token),
):
    validate_doc_file_input(file=file, file_extensions=('xlsx', 'xls'))

    sheet_name = unquote(sheet_name) if sheet_name else None

    input_file_path = get_temp_file_path(extension='xlsx')
    temp_dir = os.path.dirname(input_file_path)

    async with aiofiles.open(input_file_path, 'wb') as input_file:
        content = await file.read()
        await input_file.write(content)

    try:
        data = pd.read_excel(
            input_file_path, keep_default_na=False, header=None, dtype=str,
            sheet_name=sheet_name
        )
    except ValueError as e:
        if (
                str(e).startswith("Worksheet named ") and
                str(e).endswith(" not found")
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"The sheet name '{sheet_name}' provided does not exist in "
                    "the file."
                )
            )
        raise HTTPException(
            status_code=400,
            detail="Could not read the file"
        )
    except:
        raise HTTPException(
            status_code=400,
            detail="Could not read the file" if not sheet_name else (
                f"Could not read the file or the sheet name '{sheet_name}'."
            )
        )

    if isinstance(data, dict) and len(data.keys()) > 1:
        raise HTTPException(
            status_code=400,
            detail=(
                "There are multiple sheets in the file. Please provide "
                "the sheet name."
            )
        )
    if isinstance(data, dict):
        if not data.keys():
            raise HTTPException(status_code=400, detail="The file is empty")

        data = data[list(data.keys())[0]]  # Get the DataFrame from the dictionary

    if not isinstance(data, pd.DataFrame):
        raise HTTPException(
            status_code=400,
            detail="Could not read the file"
        )
    try:
        num_chunks = (len(data) + row_count - 1) // row_count  # Ceiling division

        if num_chunks > MAX_FILE_SPLIT:
            raise HTTPException(
                status_code=400,
                detail=MAX_FILE_SPLIT_ERROR
            )

        # Split the DataFrame into chunks
        chunks = [data.iloc[i * row_count:(i + 1) * row_count] for i in
                  range(num_chunks)]

        # Save each chunk to a new Excel file
        for index, chunk in enumerate(chunks):
            if output_format == 'xlsx':
                chunk.to_excel(
                    os.path.join(temp_dir, f'part_{index + 1}.xlsx'),
                    index=False,
                    header=None,
                    na_rep=''  # Keep NaN as empty strings in the output
                )
            else:
                chunk.to_csv(
                    os.path.join(temp_dir, f'part_{index + 1}.csv'),
                    index=False,
                    header=None,
                    na_rep=''  # Keep NaN as empty strings in the output
                )
        zip_file_name = "split_files.zip"
        zip_file_path = archive_to_zip(
            temp_dir_path=temp_dir,
            zip_file_name=zip_file_name,
            file_starts_with="part_"
        )

        background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)
        return FileResponse(
            zip_file_path, media_type='application/zip', filename=zip_file_name
        )

    except (OSError, HTTPException, Exception) as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(file_path=input_file_path)

        if isinstance(e, HTTPException):
            status_code = e.status_code
            if str(e) == MAX_FILE_SPLIT_ERROR:
                raise HTTPException(
                    status_code=status_code,
                    detail=MAX_FILE_SPLIT_ERROR
                )
            raise HTTPException(
                status_code=status_code,
                detail="Could not process the file"
            )

        raise HTTPException(
            status_code=500,
            detail="Server error"
        )
