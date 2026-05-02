import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from core.database import db
from core.security import get_current_user
from models.closure import (
    LevelBonuses, MonthlyClosureBreakdown, MonthlyClosureIn, MonthlyClosureOut,
)
from models.inventory import ReverseOverdueItem
from services.closure_pdf import render_closure_pdf
from services.inventory import compute_penalty_total, enrich_reverse_fields
from services.monthly_bonuses import compute_monthly_bonuses

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
    user = await db.users.find_one({"id": user_id}) or {}
    level = (user.get("level") or "n1").lower()

    # Ganhos brutos do mês (usando comp_final_value se existir, fallback R$0)
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
        # v14: usa comp_final_value do motor; legado continua 0 (não há fallback pois
        # substituímos 100% a lógica antiga de preço).
        total_gross += float(d.get("comp_final_value") or 0)

    # Estado do inventário (penalidades)
    inv = await db.inventory.find({"user_id": user_id}, {"_id": 0}).to_list(length=500)
    enriched = [enrich_reverse_fields(d) for d in inv]
    pen_inv = compute_penalty_total(enriched)

    # Débitos de retorno 30d (penalty_transactions do mês)
    pen_txns = await db.penalty_transactions.find(
        {"user_id": user_id, "created_at": {"$gte": start.isoformat(), "$lt": end.isoformat()}},
        {"_id": 0},
    ).to_list(length=500)
    return_penalty = sum(abs(float(t.get("amount") or 0)) for t in pen_txns)
    total_penalty = round(pen_inv["penalty_total"] + return_penalty, 2)

    # Bônus por nível (v14 Fase 4)
    bonuses_dict = await compute_monthly_bonuses(user, start.isoformat(), end.isoformat())
    bonus_total = bonuses_dict["bonus_total"]

    net = round(total_gross + bonus_total - total_penalty, 2)

    return MonthlyClosureBreakdown(
        total_gross=round(total_gross, 2),
        total_jobs=len(docs),
        inventory_total=len(enriched),
        overdue_count=pen_inv["overdue_count"],
        penalty_total=total_penalty,
        net_after_penalty=net,
        overdue_items=[ReverseOverdueItem(**x) for x in pen_inv["overdue_items"]],
        level=level,
        bonuses=LevelBonuses(**bonuses_dict),
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


@router.get("/pdf")
async def monthly_closure_pdf(month: Optional[str] = None, user=Depends(get_current_user)):
    """Gera PDF do fechamento mensal (usa snapshot confirmado se existir,
    senão gera em tempo real)."""
    if not month:
        now = datetime.now(timezone.utc)
        month = f"{now.year:04d}-{now.month:02d}"
    _parse_month(month)
    existing = await db.monthly_closures.find_one(
        {"user_id": user["id"], "month": month}, {"_id": 0},
    )
    if existing:
        closure_doc = existing
    else:
        breakdown = await _compute_breakdown(user["id"], month)
        closure_doc = {
            "user_id": user["id"],
            "month": month,
            "confirmed_at": None,
            "breakdown": breakdown.dict(),
        }
    pdf_bytes = render_closure_pdf(user, closure_doc)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=fechamento-{month}.pdf"},
    )
