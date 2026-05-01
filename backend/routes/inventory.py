from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from constants import INVENTORY_STATUSES
from core.database import db
from core.security import get_current_user
from models.inventory import InventoryItem, InventoryTransferIn

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/me", response_model=List[InventoryItem])
async def my_inventory(user=Depends(get_current_user)):
    cursor = db.inventory.find({"user_id": user["id"]}, {"_id": 0}).sort("updated_at", -1)
    return await cursor.to_list(length=500)


@router.post("/{item_id}/transfer", response_model=InventoryItem)
async def inventory_transfer(item_id: str, payload: InventoryTransferIn, user=Depends(get_current_user)):
    if payload.new_status not in INVENTORY_STATUSES:
        raise HTTPException(status_code=400, detail=f"status inválido. Use: {', '.join(INVENTORY_STATUSES)}")
    item = await db.inventory.find_one({"id": item_id, "user_id": user["id"]}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    await db.inventory.update_one(
        {"id": item_id},
        {"$set": {
            "status": payload.new_status,
            "tracking_code": payload.tracking_code or item.get("tracking_code", ""),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    updated = await db.inventory.find_one({"id": item_id}, {"_id": 0})
    return updated
