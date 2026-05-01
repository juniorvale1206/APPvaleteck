from typing import List
from fastapi import APIRouter, Depends

from core.config import SLA_FAST_SEC
from core.database import db
from core.security import get_current_user
from models.ranking import RankingEntry, RankingOut
from services.pricing import base_price, period_start, sla_bonus

router = APIRouter(prefix="/rankings", tags=["rankings"])


@router.get("/weekly", response_model=RankingOut)
async def rankings_weekly(user=Depends(get_current_user)):
    start = period_start("week")
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(length=500)
    entries: List[RankingEntry] = []
    for u in users:
        q: dict = {
            "user_id": u["id"],
            "status": {"$in": ["enviado", "em_auditoria", "aprovado", "reprovado"]},
        }
        if start is not None:
            q["$or"] = [
                {"sent_at": {"$gte": start.isoformat()}},
                {"$and": [{"sent_at": {"$in": [None, ""]}}, {"created_at": {"$gte": start.isoformat()}}]},
            ]
        cursor = db.checklists.find(q, {"_id": 0})
        docs = await cursor.to_list(length=2000)
        total_net = 0.0
        fast_count = 0
        elapsed_sum = 0
        for d in docs:
            empresa = d.get("empresa", "")
            tipo = d.get("tipo_atendimento") or "Instalação"
            base = base_price(empresa, tipo)
            elapsed = int(d.get("execution_elapsed_sec") or 0)
            bonus = sla_bonus(base, elapsed)
            total_net += base + bonus
            elapsed_sum += elapsed
            if elapsed > 0 and elapsed < SLA_FAST_SEC:
                fast_count += 1
        n = len(docs)
        avg_min = (elapsed_sum // n // 60) if n > 0 and elapsed_sum > 0 else 0
        entries.append(RankingEntry(
            user_id=u["id"],
            name=u["name"],
            email=u["email"],
            total_net=round(total_net, 2),
            count=n,
            fast_count=fast_count,
            avg_elapsed_min=avg_min,
            badge="",
            is_me=(u["id"] == user["id"]),
        ))
    earners = sorted(entries, key=lambda x: x.total_net, reverse=True)
    me_earners_pos = next((i + 1 for i, e in enumerate(earners) if e.is_me), None)
    for i, e in enumerate(earners[:5]):
        e.badge = "gold" if i == 0 else "silver" if i == 1 else "bronze" if i == 2 else ""
    top_earners = earners[:5]
    fasts = sorted(entries, key=lambda x: (-x.fast_count, x.avg_elapsed_min if x.avg_elapsed_min > 0 else 999999))
    me_fast_pos = next((i + 1 for i, e in enumerate(fasts) if e.is_me), None)
    for i, e in enumerate(fasts[:5]):
        e.badge = "gold" if i == 0 else "silver" if i == 1 else "bronze" if i == 2 else ""
    top_fast = fasts[:5]
    return RankingOut(
        period="week",
        top_earners=top_earners,
        top_fast=top_fast,
        me_earners_pos=me_earners_pos,
        me_fast_pos=me_fast_pos,
    )
