"""Endpoints administrativos — requer role=admin.

Permite ao admin visualizar:
- Fechamentos de todos os técnicos (por mês)
- Resumo consolidado de estoque de todos os técnicos
- Lista de usuários técnicos
- Aprovar/Reprovar checklists (motor de regras pós-aprovação)
- Configurar meta mensal por técnico
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.database import db
from core.security import require_admin
from services.inventory import compute_penalty_total, enrich_reverse_fields
from services.rules import apply_approval_rules, apply_rejection

router = APIRouter(prefix="/admin", tags=["admin"])


class ApprovalActionIn(BaseModel):
    reason: Optional[str] = ""      # obrigatório para reject


class SetMetaIn(BaseModel):
    monthly_target: int


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



@router.get("/pending-approvals")
async def list_pending_approvals(admin=Depends(require_admin)):
    """Lista checklists com status `enviado` aguardando aprovação."""
    cursor = db.checklists.find(
        {"status": {"$in": ["enviado", "em_auditoria"]}},
        {"_id": 0, "photos": 0, "signature_base64": 0},
    ).sort("sent_at", -1)
    docs = await cursor.to_list(length=300)
    # Enriquecer com nome do técnico
    user_ids = list({d["user_id"] for d in docs})
    users = {u["id"]: u for u in await db.users.find({"id": {"$in": user_ids}}, {"_id": 0}).to_list(length=500)}
    for d in docs:
        u = users.get(d["user_id"])
        d["technician_name"] = u.get("name") if u else "—"
        d["technician_email"] = u.get("email") if u else ""
    return {"pending": docs, "count": len(docs)}


@router.post("/checklists/{checklist_id}/approve")
async def approve_checklist(checklist_id: str, admin=Depends(require_admin)):
    """Aprova e processa um checklist executando o motor de regras.

    Regras aplicadas:
    1. Duplicidade (30 dias): checa se a placa já foi validada por QUALQUER técnico
       nos últimos 30 dias. Se sim → duplicidade_garantia (R$ 0,00).
       Se não → valido (+ R$ 5,00).
    2. Atualiza contadores para a meta mensal do técnico.
    """
    cl = await db.checklists.find_one({"id": checklist_id}, {"_id": 0})
    if not cl:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")
    if cl["status"] not in ("enviado", "em_auditoria"):
        raise HTTPException(status_code=400, detail=f"Checklist já processado (status atual: {cl['status']})")
    updated = await apply_approval_rules(checklist_id, admin)
    # v14 Fase 3B — Motor Financeiro Pós-Aprovação
    from services.compensation import compute_and_persist_compensation
    comp = await compute_and_persist_compensation(checklist_id, admin)
    # Recarrega para retornar o snapshot completo
    updated = await db.checklists.find_one({"id": checklist_id}, {"_id": 0})

    msg_parts = []
    if updated.get("validation_status") == "duplicidade_garantia":
        msg_parts.append("⚠️ Duplicidade detectada (regra antiga 30d).")
    if comp.get("comp_warranty_zero"):
        msg_parts.append(f"🔒 Garantia ({comp.get('comp_max_minutes', 0)} dias) — OS = R$ 0,00.")
    if comp.get("comp_return_flagged") and comp.get("comp_penalty_on_original"):
        msg_parts.append(f"💸 Retorno 30d — R$ {comp['comp_penalty_on_original']:.2f} debitado do técnico original.")
    if comp.get("comp_sla_cut"):
        msg_parts.append("⏱️ SLA extrapolado — valor cortado em 50%.")
    msg_parts.append(f"💰 Valor final creditado: R$ {comp.get('comp_final_value', 0):.2f}.")

    return {
        "ok": True,
        "checklist": updated,
        "validation_status": updated.get("validation_status"),
        "validation_bonus": updated.get("validation_bonus"),
        "duplicate_of": updated.get("duplicate_of"),
        "compensation": comp,
        "message": " ".join(msg_parts),
    }


@router.post("/checklists/{checklist_id}/reject")
async def reject_checklist(checklist_id: str, payload: ApprovalActionIn, admin=Depends(require_admin)):
    """Reprova um checklist com motivo obrigatório."""
    cl = await db.checklists.find_one({"id": checklist_id}, {"_id": 0})
    if not cl:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")
    if cl["status"] not in ("enviado", "em_auditoria"):
        raise HTTPException(status_code=400, detail=f"Checklist já processado (status atual: {cl['status']})")
    if not (payload.reason or "").strip():
        raise HTTPException(status_code=400, detail="Motivo da recusa é obrigatório")
    updated = await apply_rejection(checklist_id, admin, payload.reason.strip())
    return {"ok": True, "checklist": updated}


@router.post("/users/{user_id}/meta")
async def set_user_monthly_target(user_id: str, payload: SetMetaIn, admin=Depends(require_admin)):
    """Configura meta mensal customizada de um técnico (default: 60)."""
    if payload.monthly_target <= 0 or payload.monthly_target > 1000:
        raise HTTPException(status_code=400, detail="monthly_target deve estar entre 1 e 1000")
    result = await db.users.update_one(
        {"id": user_id, "role": "tecnico"},
        {"$set": {"monthly_target": payload.monthly_target}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Técnico não encontrado")
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return {"ok": True, "user": updated}
