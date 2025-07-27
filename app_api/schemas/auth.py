from typing import Optional, Literal

from pydantic import BaseModel


class TokenData(BaseModel):
    access_token: str
    username: str
    # system is for session tokens, user is for user generated tokens
    generated_by: Literal["system", "user", "openai_oauth"]
    ttl: Optional[int]  # time to live in seconds
