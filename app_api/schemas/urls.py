from typing import Literal

from pydantic import BaseModel


class CloudRunAPIEndpoint(BaseModel):
    api_url: str
    url_target: str
    is_active: bool = False
    method: Literal["GET", "POST", "PUT", "DELETE"] = "POST"
    other: dict = None


class ExternalAPIEndpoint(BaseModel):
    api_url: str
    is_active: bool = False
    method: Literal["GET", "POST", "PUT", "DELETE"] = "POST"
    other: dict = None
