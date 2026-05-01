"""Motor de regras pós-aprovação do Valeteck.

Regras implementadas:
1. Duplicidade (30 dias) — se a placa já foi validada por QUALQUER técnico nos
   últimos 30 dias, a nova OS é marcada como "duplicidade_garantia" (sem bônus).
   Caso contrário, "valido" com bônus de R$ 5,00.
2. Meta mensal — verifica se o técnico bateu a meta configurável de OS válidas
   no mês vigente (padrão 60).

Esses endpoints são consumidos pelo router admin (/api/admin/checklists/{id}/approve)
e pela gamificação do técnico (/api/gamification/meta).
"""
from calendar import monthrange
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from core.database import db


VALIDATION_BONUS = 5.00                # R$ por OS aprovada como válida
DUPLICATE_WINDOW_DAYS = 30
DEFAULT_MONTHLY_TARGET = 60


async def check_duplicate(plate_norm: str, current_id: str) -> Optional[dict]:
    """Retorna o checklist duplicado encontrado (se houver), ou None.

    Considera qualquer técnico (visão global anti-fraude).
    """
    if not plate_norm:
        return None
    since = datetime.now(timezone.utc) - timedelta(days=DUPLICATE_WINDOW_DAYS)
    doc = await db.checklists.find_one(
        {
            "plate_norm": plate_norm,
            "id": {"$ne": current_id},
            "validation_status": "valido",
            "$or": [
                {"approved_at": {"$gte": since.isoformat()}},
                {"sent_at": {"$gte": since.isoformat()}},
            ],
        },
        {"_id": 0, "id": 1, "numero": 1, "user_id": 1, "approved_at": 1, "sent_at": 1},
        sort=[("approved_at", -1)],
    )
    return doc


async def apply_approval_rules(checklist_id: str, admin_user: dict) -> dict:
    """Aprova um checklist executando as regras de validação.

    Retorna o checklist atualizado.
    """
    cl = await db.checklists.find_one({"id": checklist_id}, {"_id": 0})
    if not cl:
        raise ValueError("Checklist não encontrado")

    # Regra 1: Duplicidade
    duplicate = await check_duplicate(cl.get("plate_norm", ""), checklist_id)
    now_iso = datetime.now(timezone.utc).isoformat()
    update: dict = {
        "status": "aprovado",
        "approved_at": now_iso,
        "approved_by_id": admin_user["id"],
        "approved_by_name": admin_user.get("name", "Admin"),
        "updated_at": now_iso,
    }
    if duplicate:
        update["validation_status"] = "duplicidade_garantia"
        update["validation_bonus"] = 0.0
        update["duplicate_of"] = duplicate["id"]
    else:
        update["validation_status"] = "valido"
        update["validation_bonus"] = VALIDATION_BONUS
        update["duplicate_of"] = None

    await db.checklists.update_one({"id": checklist_id}, {"$set": update})
    updated = await db.checklists.find_one({"id": checklist_id}, {"_id": 0})
    return updated


async def apply_rejection(checklist_id: str, admin_user: dict, reason: str) -> dict:
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.checklists.update_one(
        {"id": checklist_id},
        {"$set": {
            "status": "reprovado",
            "rejected_at": now_iso,
            "approved_by_id": admin_user["id"],
            "approved_by_name": admin_user.get("name", "Admin"),
            "rejection_reason": reason,
            "validation_status": "pending",
            "validation_bonus": 0.0,
            "updated_at": now_iso,
        }},
    )
    return await db.checklists.find_one({"id": checklist_id}, {"_id": 0})


async def get_monthly_target(user: dict) -> int:
    """Retorna a meta mensal do técnico (campo `monthly_target` no doc, default 60)."""
    t = user.get("monthly_target")
    if isinstance(t, int) and t > 0:
        return t
    return DEFAULT_MONTHLY_TARGET


async def compute_meta_status(user: dict) -> dict:
    """Calcula status atual da meta mensal do técnico."""
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    last_day = monthrange(now.year, now.month)[1]
    month_end = datetime(now.year, now.month, last_day, 23, 59, 59, tzinfo=timezone.utc)

    # OS válidas no mês
    count_valid = await db.checklists.count_documents({
        "user_id": user["id"],
        "validation_status": "valido",
        "approved_at": {"$gte": month_start.isoformat(), "$lte": month_end.isoformat()},
    })
    count_pending = await db.checklists.count_documents({
        "user_id": user["id"],
        "status": {"$in": ["enviado", "em_auditoria"]},
        "sent_at": {"$gte": month_start.isoformat(), "$lte": month_end.isoformat()},
    })
    count_duplicate = await db.checklists.count_documents({
        "user_id": user["id"],
        "validation_status": "duplicidade_garantia",
        "approved_at": {"$gte": month_start.isoformat(), "$lte": month_end.isoformat()},
    })

    target = await get_monthly_target(user)
    days_left = max((month_end - now).days, 0)
    days_passed = max((now - month_start).days, 1)

    progress_pct = round(min(count_valid / target, 1.0), 3) if target > 0 else 0
    on_track_count = int(round(target * (days_passed / (days_passed + days_left)))) if days_left > 0 else target
    on_track = count_valid >= on_track_count
    remaining = max(target - count_valid, 0)
    per_day_needed = round(remaining / max(days_left, 1), 1) if days_left > 0 else float(remaining)

    return {
        "target": target,
        "achieved": count_valid,
        "pending": count_pending,
        "duplicates": count_duplicate,
        "progress_pct": progress_pct,
        "remaining": remaining,
        "days_left": days_left,
        "per_day_needed": per_day_needed,
        "on_track": on_track,
        "reached": count_valid >= target,
        "validation_bonus_earned": round(count_valid * VALIDATION_BONUS, 2),
    }
