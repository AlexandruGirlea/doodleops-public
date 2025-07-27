import logging
from typing import Union

from fastapi import UploadFile, HTTPException, status


logger = logging.getLogger(__name__)


async def validate_file_size_mb(file: UploadFile, max_size_mb: int) -> bool:
    try:
        contents = await file.read()
        await file.seek(0)
    except (AttributeError, FileNotFoundError) as e:
        msg = "File not found."

        logger.error(msg)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        ) from e
    except Exception as e:
        logger.error(f"Unknown error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unknown error. Please check file format and try again.",
        ) from e

    if len(contents) > max_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size is {max_size_mb} MB.",
        )
    return True


def validate_file_type(
        file: UploadFile,
        file_extensions: Union[tuple, set],
        content_type: tuple = None,
        content_type_startswith: str = None
) -> bool:
    try:
        if file.filename == '':
            raise HTTPException(status_code=400, detail="No selected file")

        elif len(file.filename.split('.')) == 1:
            raise HTTPException(
                status_code=400, detail="File extension not found"
            )

        elif file.filename.split('.')[-1].lower() not in file_extensions:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        elif content_type and file.content_type.lower() not in content_type:
            raise HTTPException(
                status_code=400, detail="Unsupported content type"
            )
        elif content_type_startswith and not file.content_type.startswith(
                content_type_startswith
        ):
            logger.error(
                f"File content type does not start with {content_type_startswith}"
                f" but is {file.content_type}"
            )
            raise HTTPException(
                status_code=400, detail="Unsupported content type"
            )

        return True
    except IndexError as e:
        logger.error(f"File extension not found: {e}")
        raise (
            HTTPException(
                status_code=400, detail="File extension not found"
            )
        )
    except Exception as e:
        logger.error(f"Unknown error: {e}")
        raise HTTPException(
            status_code=500, detail="Server error"
        )
