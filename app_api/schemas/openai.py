from typing import List
from pydantic import BaseModel, HttpUrl


class OpenAIFileIdRef(BaseModel):
    name: str
    id: str
    mime_type: str
    download_link: HttpUrl


class RequestModel(BaseModel):
    openaiFileIdRefs: List[OpenAIFileIdRef]


class ResponseModel(BaseModel):
    openaiFileResponse: List[str]
