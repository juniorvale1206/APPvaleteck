"""Extrato mensal do técnico (v14 — Motor de Comissionamento).

Agrega dados do mês corrente (ou qualquer mês via ?month=YYYY-MM):
- OS totais feitas (enviadas no mês)
- OS aprovadas como válidas
- OS dentro/fora do SLA
- Penalidades (duplicidade 30d e atrasos pending_reverse)
- Valor bruto estimado (usando o novo catálogo ou fallback legado)
- Progresso da meta mensal por nível
"""
from calendar import monthrange
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from core.database import db
from core.security import get_current_user
from models.service_types import (
    SERVICE_TYPES, JUNIOR_FIXED_VALUE_PER_OS,
    N1N2_MONTHLY_GOAL_THRESHOLD, JUNIOR_GOAL_BONUS_THRESHOLD,
)

router = APIRouter(prefix="/statement", tags=["statement"])


def _parse_month(month: Optional[str]) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if month:
        try:
            year, m = map(int, month.split("-"))
            if not (1 <= m <= 12):
                raise ValueError
        except Exception:
            raise HTTPException(status_code=400, detail="month inválido. Use formato YYYY-MM.")
    else:
        year, m = now.year, now.month
    start = datetime(year, m, 1, tzinfo=timezone.utc)
    last_day = monthrange(year, m)[1]
    end = datetime(year, m, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


@router.get("/me")
async def my_monthly_statement(
    month: Optional[str] = Query(None, description="YYYY-MM (opcional — default = mês atual)"),
    user=Depends(get_current_user),
):
    start, end = _parse_month(month)
    level = user.get("level") or "n1"

    # Checklists do mês (baseados em sent_at)
    query = {
        "user_id": user["id"],
        "status": {"$in": ["enviado", "em_auditoria", "aprovado", "reprovado"]},
        "sent_at": {"$gte": start.isoformat(), "$lte": end.isoformat()},
    }
    cursor = db.checklists.find(query, {"_id": 0})
    docs = await cursor.to_list(length=2000)

    total_os = len(docs)
    valid_os = 0
    duplicates = 0
    within_sla = 0
    out_sla = 0
    gross_estimated = 0.0
    by_service: dict[str, dict] = {}

    for d in docs:
        st_code = d.get("service_type_code") or ""
        st_def = SERVICE_TYPES.get(st_code)
        elapsed_min = round((d.get("execution_elapsed_sec") or 0) / 60, 1)
        v_status = d.get("validation_status") or "pending"

        # Contagens
        if v_status == "valido":
            valid_os += 1
        elif v_status == "duplicidade_garantia":
            duplicates += 1

        # SLA (só quando houver serviço e elapsed)
        within = None
        base_v = 0.0
        if st_def and elapsed_min > 0:
            within = elapsed_min <= st_def.max_minutes
            if within:
                within_sla += 1
                base_v = st_def.base_value
            else:
                out_sla += 1
                base_v = st_def.base_value / 2       # corte de 50%
        elif st_def:
            # Sem tempo registrado — assume dentro do SLA para fins de estimativa
            within_sla += 1
            base_v = st_def.base_value

        # Júnior recebe valor fixo por OS dentro do SLA (sem usar tabela R$2-10)
        if level == "junior":
            base_v = JUNIOR_FIXED_VALUE_PER_OS if (within is None or within) else 0.0

        # Duplicidade: OS com validation_status=duplicidade_garantia vale R$ 0
        if v_status == "duplicidade_garantia":
            base_v = 0.0

        gross_estimated += base_v

        # Breakdown por tipo
        key = st_code or "sem_tipo"
        b = by_service.setdefault(key, {
            "code": key,
            "name": st_def.name if st_def else "Sem tipo definido",
            "count": 0,
            "total": 0.0,
        })
        b["count"] += 1
        b["total"] += base_v

    gross_estimated = round(gross_estimated, 2)

    # Penalidades (inventário atrasado — pending_reverse)
    from services.inventory import enrich_reverse_fields, compute_penalty_total
    raw_items = await db.inventory.find(
        {"user_id": user["id"], "status": "pending_reverse"}, {"_id": 0}
    ).to_list(length=500)
    enriched = [enrich_reverse_fields(i, now=end) for i in raw_items]
    overdue = compute_penalty_total(enriched)
    penalty_total = round(overdue["penalty_total"], 2)
    penalty_count = overdue["overdue_count"]

    # Meta mensal por nível
    meta_target = JUNIOR_GOAL_BONUS_THRESHOLD if level == "junior" else N1N2_MONTHLY_GOAL_THRESHOLD
    meta_reached = valid_os >= meta_target
    sla_pct = round((within_sla / max(within_sla + out_sla, 1)) * 100, 1)

    net_after_penalty = round(gross_estimated - penalty_total, 2)

    return {
        "month": f"{start.year:04d}-{start.month:02d}",
        "level": level,
        "total_os": total_os,
        "valid_os": valid_os,
        "duplicates": duplicates,
        "within_sla": within_sla,
        "out_sla": out_sla,
        "sla_compliance_pct": sla_pct,
        "gross_estimated": gross_estimated,
        "penalty_total": penalty_total,
        "penalty_count": penalty_count,
        "net_estimated": net_after_penalty,
        "meta_target": meta_target,
        "meta_reached": meta_reached,
        "meta_remaining": max(meta_target - valid_os, 0),
        "by_service": sorted(by_service.values(), key=lambda x: -x["total"]),
    }
