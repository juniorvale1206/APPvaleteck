import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from core.database import db
from core.security import get_current_user
from models.closure import (
    MonthlyClosureBreakdown, MonthlyClosureIn, MonthlyClosureOut,
)
from models.inventory import ReverseOverdueItem
from services.inventory import compute_penalty_total, enrich_reverse_fields
from services.pricing import base_price, sla_bonus

router = APIRouter(prefix="/inventory/monthly-closure", tags=["closures"])


def _parse_month(m: str):
    try:
        y, mo = m.split("-")
        y, mo = int(y), int(mo)
        if not (1 <= mo <= 12):
            raise ValueError
        start = datetime(y, mo, 1, tzinfo=timezone.utc)
        # próximo mês
        if mo == 12:
            end = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = datetime(y, mo + 1, 1, tzinfo=timezone.utc)
        return start, end
    except Exception:
        raise HTTPException(status_code=400, detail="month inválido. Use formato YYYY-MM.")


async def _compute_breakdown(user_id: str, month: str) -> MonthlyClosureBreakdown:
    start, end = _parse_month(month)
    # Ganhos do mês
    cursor = db.checklists.find({
        "user_id": user_id,
        "status": {"$in": ["enviado", "em_auditoria", "aprovado", "reprovado"]},
        "$or": [
            {"sent_at": {"$gte": start.isoformat(), "$lt": end.isoformat()}},
            {"$and": [
                {"sent_at": {"$in": [None, ""]}},
                {"created_at": {"$gte": start.isoformat(), "$lt": end.isoformat()}},
            ]},
        ],
    }, {"_id": 0})
    docs = await cursor.to_list(length=2000)
    total_gross = 0.0
    for d in docs:
        empresa = d.get("empresa", "")
        tipo = d.get("tipo_atendimento") or "Instalação"
        base = base_price(empresa, tipo)
        elapsed = int(d.get("execution_elapsed_sec") or 0)
        bonus = sla_bonus(base, elapsed)
        total_gross += base + bonus

    # Estado do inventário
    inv = await db.inventory.find({"user_id": user_id}, {"_id": 0}).to_list(length=500)
    enriched = [enrich_reverse_fields(d) for d in inv]
    pen = compute_penalty_total(enriched)

    return MonthlyClosureBreakdown(
        total_gross=round(total_gross, 2),
        total_jobs=len(docs),
        inventory_total=len(enriched),
        overdue_count=pen["overdue_count"],
        penalty_total=round(pen["penalty_total"], 2),
        net_after_penalty=round(total_gross - pen["penalty_total"], 2),
        overdue_items=[ReverseOverdueItem(**x) for x in pen["overdue_items"]],
    )


@router.get("", response_model=MonthlyClosureOut)
async def get_monthly_closure(month: Optional[str] = None, user=Depends(get_current_user)):
    """Retorna o fechamento mensal (confirmado se existir; senão, snapshot em tempo real).
    Se `month` não for informado, usa o mês corrente.
    """
    if not month:
        now = datetime.now(timezone.utc)
        month = f"{now.year:04d}-{now.month:02d}"
    _parse_month(month)

    existing = await db.monthly_closures.find_one(
        {"user_id": user["id"], "month": month}, {"_id": 0},
    )
    if existing:
        # Retorna o snapshot confirmado
        return MonthlyClosureOut(**existing)

    breakdown = await _compute_breakdown(user["id"], month)
    return MonthlyClosureOut(
        user_id=user["id"],
        month=month,
        confirmed_at=None,
        breakdown=breakdown,
        signature_base64="",
        notes="",
    )


@router.post("/confirm", response_model=MonthlyClosureOut)
async def confirm_monthly_closure(payload: MonthlyClosureIn, user=Depends(get_current_user)):
    """Confirma o fechamento do mês (snapshot imutável + assinatura digital).
    Não permite reconfirmar o mesmo mês.
    """
    _parse_month(payload.month)
    existing = await db.monthly_closures.find_one({"user_id": user["id"], "month": payload.month})
    if existing:
        raise HTTPException(status_code=400, detail="Fechamento do mês já foi confirmado anteriormente.")
    breakdown = await _compute_breakdown(user["id"], payload.month)
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "month": payload.month,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
        "breakdown": breakdown.dict(),
        "signature_base64": payload.signature_base64 or "",
        "notes": payload.notes or "",
    }
    await db.monthly_closures.insert_one(doc)
    doc.pop("_id", None)
    return MonthlyClosureOut(**doc)


@router.get("/history")
async def list_closure_history(user=Depends(get_current_user)):
    cursor = db.monthly_closures.find({"user_id": user["id"]}, {"_id": 0}).sort("month", -1)
    docs = await cursor.to_list(length=60)
    return {"closures": docs}
