from typing import Optional
from pydantic import BaseModel


class PlateOcrIn(BaseModel):
    base64: str  # data URI or raw base64


class PlateOcrOut(BaseModel):
    plate: Optional[str] = None
    confidence: float = 0.0
    raw: str = ""
    detected: bool = False
