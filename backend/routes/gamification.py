from fastapi import APIRouter, Depends

from core.database import db
from core.security import get_current_user
from models.gamification import GamificationOut
from services.gamification import (
    compute_achievements, compute_weekly_history, compute_xp, level_from_xp,
)
from services.rules import compute_meta_status

router = APIRouter(prefix="/gamification", tags=["gamification"])


@router.get("/meta")
async def gamification_meta(user=Depends(get_current_user)):
    """Status da meta mensal do técnico (60 OS válidas por padrão)."""
    return await compute_meta_status(user)


@router.get("/profile", response_model=GamificationOut)
async def gamification_profile(user=Depends(get_current_user)):
    cursor = db.checklists.find(
        {"user_id": user["id"], "status": {"$in": ["enviado", "em_auditoria", "aprovado", "reprovado"]}},
        {"_id": 0},
    )
    docs = await cursor.to_list(length=5000)
    xp = compute_xp(docs)
    level = level_from_xp(xp)
    ach = compute_achievements(docs)
    weekly = compute_weekly_history(docs, weeks=8)
    unlocked_count = sum(1 for a in ach if a["unlocked"])
    return GamificationOut(
        level=level,
        achievements=ach,
        weekly_history=weekly,
        total_xp=xp,
        unlocked_count=unlocked_count,
        achievements_total=len(ach),
    )
