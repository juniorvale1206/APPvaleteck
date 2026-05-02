"""Motor Financeiro Pós-Aprovação do Valeteck (v14 — Fase 3B).

Ao admin aprovar uma OS, este módulo calcula o valor final aplicando:

  A. SLA (Corte de 50%)
     - Se tempo_execução > max_minutes do tipo de serviço → valor_base / 2.
  B. Qualidade (Placa + tipo de serviço repetidos)
     - Garantia <90d (mesma placa + mesmo tipo) → OS = R$ 0,00.
     - Retorno  <30d (mesma placa + mesmo tipo) → débito automático R$ 30 no
       TÉCNICO ORIGINAL (registrado na coleção `penalty_transactions`).
  C. Regras por nível
     - Júnior : valor fixo R$ 1,00 (substitui tabela).
     - N1/N2  : tabela de SLA oficial.
     - N3     : tabela de SLA oficial (pode atender como qualquer nível).
     - Júnior: sem bônus mensal retroativo por OS (vai via fechamento).

Persiste o snapshot de cálculo no próprio documento do checklist:
  comp_base_value     — valor da tabela antes de regras
  comp_sla_cut        — true se cortou 50%
  comp_warranty_zero  — true se anulou por garantia (mesma placa+tipo em 90d)
  comp_return_flagged — true se é um retorno (30d mesmo placa+tipo)
  comp_final_value    — valor final creditado a este técnico
  comp_penalty_on_original — R$ debitado do técnico original (quando é retorno)
  comp_previous_os_id — id da OS anterior (garantia/retorno)
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid

from core.database import db
from models.service_types import (
    SERVICE_TYPES, JUNIOR_FIXED_VALUE_PER_OS,
    RETURN_PENALTY_VALUE, WARRANTY_WINDOW_DAYS, RETURN_WINDOW_DAYS,
)


async def _find_previous_same_plate_type(plate_norm: str, service_type_code: str, current_id: str,
                                         days: int) -> Optional[dict]:
    """Retorna a OS anterior válida mais recente com mesma placa+tipo nos últimos `days` dias."""
    if not plate_norm or not service_type_code:
        return None
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return await db.checklists.find_one(
        {
            "plate_norm": plate_norm,
            "service_type_code": service_type_code,
            "id": {"$ne": current_id},
            "validation_status": "valido",
            "$or": [
                {"approved_at": {"$gte": since.isoformat()}},
                {"sent_at": {"$gte": since.isoformat()}},
            ],
        },
        {"_id": 0, "id": 1, "user_id": 1, "numero": 1, "approved_at": 1, "sent_at": 1,
         "comp_final_value": 1, "sla_base_value": 1},
        sort=[("approved_at", -1)],
    )


async def compute_and_persist_compensation(checklist_id: str, admin_user: dict) -> dict:
    """Motor financeiro executado após a aprovação (admin aprovou a OS).

    Retorna dict com breakdown, também gravado no próprio checklist.
    """
    cl = await db.checklists.find_one({"id": checklist_id}, {"_id": 0})
    if not cl:
        raise ValueError("Checklist não encontrado")

    user = await db.users.find_one({"id": cl["user_id"]})
    level = (user or {}).get("level") or "n1"

    st_code = cl.get("service_type_code") or ""
    st = SERVICE_TYPES.get(st_code)
    base_value = float(st.base_value) if st else 0.0
    max_minutes = int(st.max_minutes) if st else 0

    elapsed_sec = int(cl.get("sla_total_sec") or cl.get("execution_elapsed_sec") or 0)
    elapsed_min = elapsed_sec / 60.0

    # --- Regra A: SLA (corte 50%) ---
    sla_cut = False
    if st and max_minutes > 0 and elapsed_min > max_minutes:
        base_value = round(base_value / 2.0, 2)
        sla_cut = True

    # --- Regra de Nível — Júnior substitui tabela por R$ 1,00 fixo ---
    if level == "junior":
        base_value = JUNIOR_FIXED_VALUE_PER_OS if not sla_cut else 0.0
    # (N1/N2/N3 usam tabela)

    plate_norm = cl.get("plate_norm", "")
    # --- Regra B1: Garantia <90d (mesmo plate+tipo) ---
    warranty = await _find_previous_same_plate_type(plate_norm, st_code, checklist_id,
                                                    days=WARRANTY_WINDOW_DAYS)
    warranty_zero = False
    return_flagged = False
    penalty_on_original = 0.0
    previous_os_id: Optional[str] = None
    previous_user_id: Optional[str] = None

    if warranty:
        # Existe OS anterior — validar se cai em janela de retorno (30d) ou apenas garantia (90d)
        previous_os_id = warranty["id"]
        previous_user_id = warranty.get("user_id")
        prev_date_iso = warranty.get("approved_at") or warranty.get("sent_at")
        if prev_date_iso:
            try:
                prev_dt = datetime.fromisoformat(prev_date_iso.replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - prev_dt).days
            except Exception:
                age_days = WARRANTY_WINDOW_DAYS + 1
            if age_days <= RETURN_WINDOW_DAYS:
                return_flagged = True

        # Dentro de 90d → OS atual vai para R$ 0 (garantia)
        warranty_zero = True
        final_value = 0.0

        # Dentro de 30d → débito R$ 30 no técnico original (retorno)
        if return_flagged and previous_user_id:
            penalty_on_original = RETURN_PENALTY_VALUE
            now_iso = datetime.now(timezone.utc).isoformat()
            await db.penalty_transactions.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": previous_user_id,      # técnico ORIGINAL leva o débito
                "origin_checklist_id": previous_os_id,
                "trigger_checklist_id": checklist_id,
                "trigger_user_id": cl["user_id"],
                "plate_norm": plate_norm,
                "service_type_code": st_code,
                "amount": -RETURN_PENALTY_VALUE,
                "reason": "retorno_30d",
                "created_at": now_iso,
                "created_by": admin_user["id"],
            })
    else:
        final_value = base_value

    snapshot = {
        "comp_base_value": round(base_value, 2),
        "comp_sla_cut": sla_cut,
        "comp_warranty_zero": warranty_zero,
        "comp_return_flagged": return_flagged,
        "comp_final_value": round(final_value, 2),
        "comp_penalty_on_original": round(penalty_on_original, 2),
        "comp_previous_os_id": previous_os_id,
        "comp_previous_user_id": previous_user_id,
        "comp_level_applied": level,
        "comp_elapsed_min": round(elapsed_min, 1),
        "comp_max_minutes": max_minutes,
        "comp_computed_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.checklists.update_one({"id": checklist_id}, {"$set": snapshot})
    return snapshot


async def list_user_penalties(user_id: str, since_iso: Optional[str] = None) -> list[dict]:
    """Lista débitos (penalty_transactions) do técnico original no período."""
    q: dict = {"user_id": user_id}
    if since_iso:
        q["created_at"] = {"$gte": since_iso}
    cur = db.penalty_transactions.find(q, {"_id": 0}).sort("created_at", -1)
    return await cur.to_list(length=500)
