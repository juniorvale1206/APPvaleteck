from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from constants import INVENTORY_STATUSES
from core.database import db
from core.security import get_current_user
from models.inventory import (
    InventoryItem, InventoryTransferIn, InventorySummary, ReverseOverdueItem,
)
from services.inventory import (
    categorize_equipment, compute_penalty_total, compute_reverse_deadline,
    default_equipment_value, enrich_reverse_fields,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


CARRIERS = ["Correios", "Jadlog", "Mercado Envios", "Total Express", "Loggi", "Outro"]


@router.get("/me", response_model=List[InventoryItem])
async def my_inventory(user=Depends(get_current_user)):
    cursor = db.inventory.find({"user_id": user["id"]}, {"_id": 0}).sort("updated_at", -1)
    docs = await cursor.to_list(length=500)
    return [enrich_reverse_fields(d) for d in docs]


@router.get("/summary", response_model=InventorySummary)
async def inventory_summary(user=Depends(get_current_user)):
    cursor = db.inventory.find({"user_id": user["id"]}, {"_id": 0})
    docs = await cursor.to_list(length=500)
    enriched = [enrich_reverse_fields(d) for d in docs]
    by_status: dict = {}
    for d in enriched:
        s = d.get("status", "")
        by_status[s] = by_status.get(s, 0) + 1
    penalty = compute_penalty_total(enriched)
    return InventorySummary(
        total=len(enriched),
        by_status=by_status,
        with_tech_count=by_status.get("with_tech", 0),
        installed_count=by_status.get("installed", 0),
        pending_reverse_count=by_status.get("pending_reverse", 0),
        overdue_count=penalty["overdue_count"],
        penalty_total=penalty["penalty_total"],
        overdue_items=[ReverseOverdueItem(**x) for x in penalty["overdue_items"]],
    )


@router.get("/carriers")
async def list_carriers():
    """Lista de transportadoras sugeridas para logística reversa."""
    return {"carriers": CARRIERS}


@router.post("/{item_id}/transfer", response_model=InventoryItem)
async def inventory_transfer(item_id: str, payload: InventoryTransferIn, user=Depends(get_current_user)):
    if payload.new_status not in INVENTORY_STATUSES:
        raise HTTPException(status_code=400, detail=f"status inválido. Use: {', '.join(INVENTORY_STATUSES)}")
    item = await db.inventory.find_one({"id": item_id, "user_id": user["id"]}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    now = datetime.now(timezone.utc)
    update: dict = {
        "status": payload.new_status,
        "updated_at": now.isoformat(),
    }

    # Compat: campo tracking_code legacy (usado para in_transit_to_tech)
    if payload.tracking_code:
        update["tracking_code"] = payload.tracking_code

    # Garantir categorização/valor
    if not item.get("equipment_category"):
        cat = categorize_equipment(item.get("tipo", ""), item.get("modelo", ""))
        update["equipment_category"] = cat
        update["equipment_value"] = item.get("equipment_value") or default_equipment_value(cat)

    # Transições específicas de logística reversa --------------------
    if payload.new_status == "pending_reverse":
        # Se já estava em pending_reverse, preserva a data original (não reinicia prazo)
        if item.get("status") != "pending_reverse" or not item.get("pending_reverse_at"):
            update["pending_reverse_at"] = now.isoformat()
            update["reverse_deadline_at"] = compute_reverse_deadline(now).isoformat()

    elif payload.new_status == "in_transit_to_hq":
        # Exige carrier + tracking
        carrier = (payload.reverse_carrier or "").strip()
        trk = (payload.reverse_tracking_code or payload.tracking_code or "").strip()
        if not carrier:
            raise HTTPException(status_code=400, detail="reverse_carrier é obrigatório (transportadora)")
        if not trk:
            raise HTTPException(status_code=400, detail="reverse_tracking_code é obrigatório")
        update["reverse_carrier"] = carrier
        update["reverse_tracking_code"] = trk
        update["reverse_sent_at"] = (payload.reverse_sent_at or now.isoformat())
        if payload.reverse_expected_at:
            update["reverse_expected_at"] = payload.reverse_expected_at
        if payload.reverse_notes:
            update["reverse_notes"] = payload.reverse_notes

    elif payload.new_status == "received_at_hq":
        update["reverse_received_at"] = now.isoformat()

    await db.inventory.update_one({"id": item_id}, {"$set": update})
    updated = await db.inventory.find_one({"id": item_id}, {"_id": 0})
    return enrich_reverse_fields(updated)
