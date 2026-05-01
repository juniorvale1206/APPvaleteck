"""Endpoints administrativos — requer role=admin.

Permite ao admin visualizar:
- Fechamentos de todos os técnicos (por mês)
- Resumo consolidado de estoque de todos os técnicos
- Lista de usuários técnicos
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends

from core.database import db
from core.security import require_admin
from services.inventory import compute_penalty_total, enrich_reverse_fields

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/technicians")
async def list_technicians(admin=Depends(require_admin)):
    """Lista todos os técnicos (users com role=tecnico)."""
    cursor = db.users.find({"role": "tecnico"}, {"_id": 0, "password_hash": 0}).sort("name", 1)
    docs = await cursor.to_list(length=500)
    return {"technicians": docs}


@router.get("/inventory/summary")
async def admin_inventory_summary(admin=Depends(require_admin)):
    """Agregado do inventário de TODOS os técnicos."""
    cursor = db.inventory.find({}, {"_id": 0})
    docs = await cursor.to_list(length=5000)
    enriched = [enrich_reverse_fields(d) for d in docs]

    # agrupa por técnico
    users = {u["id"]: u for u in await db.users.find({"role": "tecnico"}, {"_id": 0}).to_list(length=500)}
    by_user: dict = {}
    total_overdue = 0
    total_penalty = 0.0
    by_status: dict = {}

    for d in enriched:
        uid = d.get("user_id")
        u = users.get(uid)
        if not u:
            continue
        if uid not in by_user:
            by_user[uid] = {
                "user_id": uid,
                "name": u["name"],
                "email": u["email"],
                "total": 0,
                "overdue": 0,
                "penalty": 0.0,
                "by_status": {},
            }
        st = d.get("status", "")
        by_user[uid]["total"] += 1
        by_user[uid]["by_status"][st] = by_user[uid]["by_status"].get(st, 0) + 1
        by_status[st] = by_status.get(st, 0) + 1
        if d.get("reverse_overdue"):
            by_user[uid]["overdue"] += 1
            by_user[uid]["penalty"] = round(
                by_user[uid]["penalty"] + float(d.get("equipment_value") or 0), 2,
            )
            total_overdue += 1
            total_penalty += float(d.get("equipment_value") or 0)

    return {
        "total_items": len(enriched),
        "total_technicians": len(by_user),
        "total_overdue": total_overdue,
        "total_penalty": round(total_penalty, 2),
        "by_status": by_status,
        "by_technician": sorted(by_user.values(), key=lambda x: x["penalty"], reverse=True),
    }


@router.get("/closures")
async def admin_closures(month: Optional[str] = None, admin=Depends(require_admin)):
    """Lista fechamentos mensais de TODOS os técnicos.
    Se `month` for informado, filtra só aquele mês.
    Inclui snapshot em tempo real para técnicos que ainda não confirmaram o mês.
    """
    if not month:
        now = datetime.now(timezone.utc)
        month = f"{now.year:04d}-{now.month:02d}"

    technicians = await db.users.find({"role": "tecnico"}, {"_id": 0, "password_hash": 0}).to_list(length=500)
    results = []

    for u in technicians:
        uid = u["id"]
        confirmed = await db.monthly_closures.find_one(
            {"user_id": uid, "month": month}, {"_id": 0},
        )
        if confirmed:
            results.append({
                "technician": {"id": uid, "name": u["name"], "email": u["email"]},
                "month": month,
                "confirmed_at": confirmed.get("confirmed_at"),
                "breakdown": confirmed.get("breakdown", {}),
                "confirmed": True,
            })
        else:
            # snapshot em tempo real (simplificado)
            from routes.closures import _compute_breakdown
            bd = await _compute_breakdown(uid, month)
            results.append({
                "technician": {"id": uid, "name": u["name"], "email": u["email"]},
                "month": month,
                "confirmed_at": None,
                "breakdown": bd.dict(),
                "confirmed": False,
            })

    total_gross = sum(r["breakdown"].get("total_gross", 0) for r in results)
    total_penalty = sum(r["breakdown"].get("penalty_total", 0) for r in results)
    total_net = sum(r["breakdown"].get("net_after_penalty", 0) for r in results)

    return {
        "month": month,
        "total_technicians": len(results),
        "confirmed_count": sum(1 for r in results if r["confirmed"]),
        "totals": {
            "gross": round(total_gross, 2),
            "penalty": round(total_penalty, 2),
            "net": round(total_net, 2),
        },
        "results": results,
    }
