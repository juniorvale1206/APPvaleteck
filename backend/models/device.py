from pydantic import BaseModel


class DeviceTestIn(BaseModel):
    imei: str


class DeviceTestOut(BaseModel):
    online: bool
    latency_ms: int
    message: str
    tested_at: str
    source: str = "mock"
