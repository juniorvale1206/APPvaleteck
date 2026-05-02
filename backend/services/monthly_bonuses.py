"""Cálculo de bônus mensais por nível (v14 Fase 4).

Aplica as regras C do Motor de Comissionamento:

  - Júnior  : +R$ 50 se valid_os >= 30
              +R$ 50 se returns_30d == 0
  - N1/N2   : +R$ 2 retroativo × within_sla_os se valid_os >= 60
  - N3      : R$ 1 residual por cada OS de cada júnior vinculado
              +R$ 1 extra por OS SE júnior bateu meta (>=30 OS)
              GUILHOTINA: zero bônus residual se júnior teve >=1 retorno no mês
"""
from datetime import datetime
from typing import Optional

from core.database import db
from models.service_types import (
    JUNIOR_GOAL_BONUS_THRESHOLD, JUNIOR_GOAL_BONUS_VALUE, JUNIOR_ZERO_RETURNS_BONUS_VALUE,
    N1N2_MONTHLY_GOAL_THRESHOLD, N1N2_MONTHLY_GOAL_BONUS_PER_OS,
    TUTOR_RESIDUAL_PER_JUNIOR_OS, TUTOR_BONUS_JUNIOR_GOAL,
)


async def _count_user_month(user_id: str, start_iso: str, end_iso: str) -> dict:
    """Conta OS do mês por status e SLA para cálculo de bônus."""
    docs = await db.checklists.find(
        {
            "user_id": user_id,
            "status": {"$in": ["enviado", "em_auditoria", "aprovado", "reprovado"]},
            "sent_at": {"$gte": start_iso, "$lt": end_iso},
        },
        {"_id": 0, "validation_status": 1, "sla_within": 1, "comp_return_flagged": 1,
         "comp_final_value": 1, "comp_sla_cut": 1},
    ).to_list(length=5000)
    valid_os = sum(1 for d in docs if d.get("validation_status") == "valido")
    within_sla_os = sum(1 for d in docs if d.get("sla_within") is True and not d.get("comp_sla_cut"))
    returns_30d = sum(1 for d in docs if d.get("comp_return_flagged"))
    return {
        "total": len(docs),
        "valid_os": valid_os,
        "within_sla_os": within_sla_os,
        "returns_30d": returns_30d,
    }


async def compute_monthly_bonuses(user: dict, start_iso: str, end_iso: str) -> dict:
    """Retorna dict com breakdown de bônus mensais para o usuário."""
    level = (user.get("level") or "n1").lower()

    # Conta OS do próprio técnico
    my = await _count_user_month(user["id"], start_iso, end_iso)
    valid_os = my["valid_os"]
    within_sla_os = my["within_sla_os"]
    returns_30d = my["returns_30d"]

    bonuses = {
        "valid_os": valid_os,
        "within_sla_os": within_sla_os,
        "returns_30d": returns_30d,
        "tutee_total_os": 0,
        "tutees_hit_goal": 0,
        "tutees_with_returns": 0,
        "bonus_junior_meta": 0.0,
        "bonus_junior_zero_returns": 0.0,
        "bonus_n1n2_retroactive": 0.0,
        "bonus_n3_residual": 0.0,
        "bonus_n3_tutoria": 0.0,
    }

    if level == "junior":
        # +R$50 se bateu 30 OS
        if valid_os >= JUNIOR_GOAL_BONUS_THRESHOLD:
            bonuses["bonus_junior_meta"] = JUNIOR_GOAL_BONUS_VALUE
        # +R$50 se teve 0 retornos
        if returns_30d == 0 and valid_os > 0:
            bonuses["bonus_junior_zero_returns"] = JUNIOR_ZERO_RETURNS_BONUS_VALUE

    elif level in ("n1", "n2"):
        # +R$2 retroativo por OS dentro do SLA se bateu 60
        if valid_os >= N1N2_MONTHLY_GOAL_THRESHOLD:
            bonuses["bonus_n1n2_retroactive"] = round(
                within_sla_os * N1N2_MONTHLY_GOAL_BONUS_PER_OS, 2,
            )

    elif level == "n3":
        # Varre juniores vinculados
        tutees = await db.users.find(
            {"tutor_id": user["id"], "level": "junior"}, {"_id": 0, "id": 1}
        ).to_list(length=50)
        residual = 0.0
        tutoria = 0.0
        tutee_total = 0
        hit = 0
        with_returns = 0
        for t in tutees:
            t_stats = await _count_user_month(t["id"], start_iso, end_iso)
            t_total = t_stats["total"]
            t_valid = t_stats["valid_os"]
            t_returns = t_stats["returns_30d"]
            tutee_total += t_total
            # Guilhotina: se tutorado teve retorno 30d, ZERO bônus deste junior
            if t_returns > 0:
                with_returns += 1
                continue
            # Residual de R$ 1 por OS do junior
            residual += t_total * TUTOR_RESIDUAL_PER_JUNIOR_OS
            # Se junior bateu meta (>=30 OS), +R$1 extra por OS
            if t_valid >= JUNIOR_GOAL_BONUS_THRESHOLD:
                hit += 1
                tutoria += t_total * TUTOR_BONUS_JUNIOR_GOAL
        bonuses["tutee_total_os"] = tutee_total
        bonuses["tutees_hit_goal"] = hit
        bonuses["tutees_with_returns"] = with_returns
        bonuses["bonus_n3_residual"] = round(residual, 2)
        bonuses["bonus_n3_tutoria"] = round(tutoria, 2)

    bonuses["bonus_total"] = round(
        bonuses["bonus_junior_meta"] + bonuses["bonus_junior_zero_returns"]
        + bonuses["bonus_n1n2_retroactive"]
        + bonuses["bonus_n3_residual"] + bonuses["bonus_n3_tutoria"],
        2,
    )
    return bonuses
