import os
import logging
from urllib.parse import unquote

import aiofiles
import pandas as pd
from natsort import natsorted
from fastapi import APIRouter
from fastapi import (
    File, UploadFile, HTTPException, BackgroundTasks, Depends, Query
)
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
    cleanup_temp_dir, get_temp_file_path, validate_doc_file_input,
    EXCEL_MEDIA_TYPE,
)

logger = logging.getLogger(__name__)

docs_excel_merge_router = APIRouter(
    tags=["Excel"],
    responses={404: {"description": "Not found"}},
)


ERRORS = {
    "MAX_FILE_COUNT": "You can upload a maximum of 20 files",
    "SERVER_ERROR": "Server error",
    "FAILED_MERGE_ERROR": "Failed to merge data excel files",
    "NO_DATA_ERROR": "No data could be read from the provided files.",
    "NO_SHEET_ERROR": "The sheet name provided does not exist in all the files.",
    "COULD_NOT_READ_FILE": "Could not read the file"
}


@docs_excel_merge_router.post(
    urls.get("excel").get("merge"),
    include_in_schema=True,
)
async def excel_merge(
        background_tasks: BackgroundTasks,
        files: list[UploadFile] = File(...),
        sheet_name: str = Query(None, min_length=1, max_length=31),
        use_upload_order: bool = Query(False),
        token_data: bool = Depends(verify_token),
):
    sheet_name = unquote(sheet_name) if sheet_name else None
    if len(files) > 20:
        raise HTTPException(
            status_code=400, detail=ERRORS["MAX_FILE_COUNT"]
        )

    for file in files:
        validate_doc_file_input(file=file, file_extensions=('xlsx', 'xls'))

    output_file_path = get_temp_file_path(extension='xlsx')
    temp_dir = os.path.dirname(output_file_path)

    # check if file names are unique
    if len(files) != len(set([file.filename for file in files])):
        raise HTTPException(
            status_code=400,
            detail="File names must be unique"
        )

    try:
        file_paths = []
        for file in files:
            input_file_path = os.path.join(temp_dir, file.filename)
            async with aiofiles.open(input_file_path, 'wb') as f:
                await f.write(await file.read())

            file_paths.append(input_file_path)

        if not use_upload_order:
            file_paths = natsorted(file_paths)

        all_data_frames = []

        # Iterate through each file path
        for file_path in file_paths:
            try:
                data = pd.read_excel(
                    file_path, sheet_name=sheet_name, header=None,
                    keep_default_na=False, dtype=str
                )

                if isinstance(data, dict):
                    for sheet_name, df_sheet in data.items():
                        all_data_frames.append(df_sheet)
                elif isinstance(data, pd.DataFrame):
                    all_data_frames.append(data)
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=ERRORS["NO_SHEET_ERROR"]
                    )
            except FileNotFoundError:
                raise HTTPException(
                    status_code=400,
                    detail=ERRORS["SERVER_ERROR"]
                )
            except Exception as e:
                logging.error(f"Error reading file {file_path}: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=(
                            ERRORS["COULD_NOT_READ_FILE"] +
                            f" {os.path.basename(file_path)}"
                    )
                )

        if not all_data_frames:
            raise HTTPException(status_code=400, detail=ERRORS["NO_DATA_ERROR"])

        # Concatenate all dataframes into one
        combined_df = pd.concat(all_data_frames, ignore_index=True)

        try:
            # Write the combined DataFrame to a new Excel file
            combined_df.to_excel(
                output_file_path, index=False, header=False, na_rep=''
            )
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Failed to merge data excel files"
            )

        file_order_str = ",".join([os.path.basename(path) for path in file_paths])

        headers = {
            "X-File-Order": file_order_str
        }

        background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)

        return FileResponse(
            output_file_path,
            media_type=EXCEL_MEDIA_TYPE,
            filename='merged_file.xlsx',
            headers=headers
        )

    except (OSError, Exception, HTTPException) as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(file_path=output_file_path)

        if isinstance(e, HTTPException):
            if str(e) in ERRORS.values() or e.status_code == 400:
                raise HTTPException(
                    status_code=e.status_code,
                    detail=str(e)
                )

        raise HTTPException(
            status_code=500,
            detail="Server error"
        )
