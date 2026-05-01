"""Detecção de duplicidades / possíveis fraudes a partir do histórico de checklists."""
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from core.database import db
from services.plates import normalize_plate
from models.checklist import ChecklistInput


async def build_alerts(payload: ChecklistInput, user_id: str, exclude_id: Optional[str] = None) -> List[str]:
    alerts: List[str] = []
    plate = normalize_plate(payload.placa)
    if not plate:
        return alerts
    now = datetime.now(timezone.utc)
    horizon_30 = now - timedelta(days=30)
    q = {"plate_norm": plate, "status": {"$in": ["enviado", "em_auditoria", "aprovado"]}}
    if exclude_id:
        q["id"] = {"$ne": exclude_id}
    cursor = db.checklists.find(q, {"_id": 0, "id": 1, "created_at": 1, "tipo_atendimento": 1, "user_id": 1})
    docs = await cursor.to_list(length=50)
    for d in docs:
        try:
            created = datetime.fromisoformat(d["created_at"].replace("Z", "+00:00"))
        except Exception:
            continue
        if created >= now - timedelta(hours=24):
            alerts.append("Possível duplicidade: já existe checklist enviado para esta placa nas últimas 24h.")
            break
    for d in docs:
        try:
            created = datetime.fromisoformat(d["created_at"].replace("Z", "+00:00"))
        except Exception:
            continue
        if created >= horizon_30 and d.get("tipo_atendimento") == "Instalação":
            if payload.tipo_atendimento in ("Manutenção", "Garantia", "Retirada"):
                alerts.append("Atenção: instalação realizada nos últimos 30 dias — possível garantia.")
                break
    return list(dict.fromkeys(alerts))
