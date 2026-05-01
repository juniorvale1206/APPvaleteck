from typing import Optional
from pydantic import BaseModel


class InventoryItem(BaseModel):
    id: str
    user_id: Optional[str] = None
    tipo: str  # rastreador | bloqueador | acessório
    modelo: str
    imei: Optional[str] = ""
    iccid: Optional[str] = ""
    serie: Optional[str] = ""
    empresa: Optional[str] = ""
    status: str
    checklist_id: Optional[str] = None
    placa: Optional[str] = ""
    tracking_code: Optional[str] = ""
    updated_at: str
    created_at: str


class InventoryTransferIn(BaseModel):
    new_status: str
    tracking_code: Optional[str] = ""
