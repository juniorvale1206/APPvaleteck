from typing import List
from fastapi import APIRouter, Depends, HTTPException

from core.config import SLA_FAST_SEC, SLA_FAST_BONUS_PCT
from core.database import db
from core.security import get_current_user
from models.earnings import EarningJob, EarningsSummary
from services.pricing import PRICE_TABLE, base_price, period_start, sla_bonus, DEFAULT_PRICE

router = APIRouter(prefix="/earnings", tags=["earnings"])


@router.get("/price-table")
async def earnings_price_table():
    return {
        "price_table": PRICE_TABLE,
        "default": DEFAULT_PRICE,
        "sla_fast_minutes": SLA_FAST_SEC // 60,
        "sla_fast_bonus_pct": SLA_FAST_BONUS_PCT,
    }


@router.get("/me", response_model=EarningsSummary)
async def my_earnings(period: str = "month", user=Depends(get_current_user)):
    if period not in ("day", "week", "month", "all"):
        raise HTTPException(status_code=400, detail="period inválido (day|week|month|all)")
    start = period_start(period)
    query: dict = {
        "user_id": user["id"],
        "status": {"$in": ["enviado", "em_auditoria", "aprovado", "reprovado"]},
    }
    if start is not None:
        query["$or"] = [
            {"sent_at": {"$gte": start.isoformat()}},
            {"$and": [{"sent_at": {"$in": [None, ""]}}, {"created_at": {"$gte": start.isoformat()}}]},
        ]
    cursor = db.checklists.find(query, {"_id": 0}).sort("sent_at", -1)
    docs = await cursor.to_list(length=2000)

    jobs: List[EarningJob] = []
    total_base = 0.0
    total_bonus = 0.0
    total_elapsed = 0
    fast_count = 0
    by_company: dict = {}
    by_type: dict = {}

    for d in docs:
        empresa = d.get("empresa", "")
        tipo = d.get("tipo_atendimento") or "Instalação"
        base = base_price(empresa, tipo)
        elapsed = int(d.get("execution_elapsed_sec") or 0)
        bonus = sla_bonus(base, elapsed)
        # Bônus de validação (R$ 5 pós-aprovação se valido)
        val_bonus = float(d.get("validation_bonus") or 0)
        total_bonus_piece = bonus + val_bonus
        net = round(base + total_bonus_piece, 2)
        fast = elapsed > 0 and elapsed < SLA_FAST_SEC
        total_base += base
        total_bonus += total_bonus_piece
        total_elapsed += elapsed
        if fast:
            fast_count += 1
        by_company[empresa] = round(by_company.get(empresa, 0.0) + net, 2)
        by_type[tipo] = round(by_type.get(tipo, 0.0) + net, 2)
        jobs.append(EarningJob(
            id=d["id"],
            numero=d["numero"],
            empresa=empresa,
            tipo_atendimento=tipo,
            nome=d.get("nome", ""),
            sobrenome=d.get("sobrenome", ""),
            placa=d.get("placa", ""),
            base_amount=round(base, 2),
            bonus_amount=round(total_bonus_piece, 2),
            total_amount=net,
            elapsed_sec=elapsed,
            elapsed_min=elapsed // 60,
            sla_fast=fast,
            sent_at=d.get("sent_at"),
            created_at=d.get("created_at"),
        ))
    count = len(jobs)
    avg_min = (total_elapsed // count // 60) if count > 0 and total_elapsed > 0 else 0

    # Penalidades de equipamentos não devolvidos (Fase 2)
    # Independentes do período - pegamos o estado atual do inventário.
    inv_cursor = db.inventory.find({"user_id": user["id"]}, {"_id": 0})
    inv_docs = await inv_cursor.to_list(length=500)
    from services.inventory import compute_penalty_total, enrich_reverse_fields
    enriched_inv = [enrich_reverse_fields(d) for d in inv_docs]
    penalty = compute_penalty_total(enriched_inv)
    penalty_total = penalty["penalty_total"]
    penalty_count = penalty["overdue_count"]
    total_net_gross = round(total_base + total_bonus, 2)

    return EarningsSummary(
        period=period,
        total_base=round(total_base, 2),
        total_bonus=round(total_bonus, 2),
        total_net=total_net_gross,
        count=count,
        avg_elapsed_min=avg_min,
        fast_count=fast_count,
        breakdown_by_company=by_company,
        breakdown_by_type=by_type,
        jobs=jobs,
        price_table=PRICE_TABLE,
        penalty_total=round(penalty_total, 2),
        penalty_count=penalty_count,
        net_after_penalty=round(total_net_gross - penalty_total, 2),
    )
