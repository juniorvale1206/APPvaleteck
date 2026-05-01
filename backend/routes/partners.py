import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from constants import PARTNER_EMPRESA_MAP
from core.config import PARTNER_WEBHOOK_SECRET
from core.database import db
from models.partner import PartnerAppointmentWebhook

router = APIRouter(prefix="/partners", tags=["partners"])


@router.post("/webhook/appointments")
async def partner_webhook_appointments(payload: PartnerAppointmentWebhook):
    """Endpoint de entrada para parceiros criarem OS no Valeteck."""
    if (payload.secret or "") != PARTNER_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="secret inválido")
    partner_key = (payload.partner or "").lower().strip()
    empresa = PARTNER_EMPRESA_MAP.get(partner_key)
    if not empresa:
        raise HTTPException(
            status_code=400,
            detail=f"partner desconhecido. Use um de: {list(PARTNER_EMPRESA_MAP.keys())}",
        )
    user = await db.users.find_one({"email": payload.user_email.lower().strip()})
    if not user:
        raise HTTPException(status_code=404, detail="Técnico (user_email) não encontrado")
    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "numero_os": payload.numero_os,
        "cliente_nome": payload.cliente_nome,
        "cliente_sobrenome": payload.cliente_sobrenome,
        "placa": (payload.placa or "").upper(),
        "empresa": empresa,
        "endereco": payload.endereco,
        "scheduled_at": payload.scheduled_at,
        "status": "agendado",
        "checklist_id": None,
        "vehicle_type": payload.vehicle_type or "carro",
        "vehicle_brand": payload.vehicle_brand or "",
        "vehicle_model": payload.vehicle_model or "",
        "vehicle_year": payload.vehicle_year or "",
        "prioridade": payload.prioridade or "normal",
        "telefone": payload.telefone or "",
        "tempo_estimado_min": payload.tempo_estimado_min or 60,
        "observacoes": payload.observacoes or "",
        "comissao": payload.comissao,
        "partner_origin": partner_key,
        "created_at": now_iso,
    }
    await db.appointments.insert_one(doc)
    doc.pop("_id", None)
    return {"ok": True, "appointment_id": doc["id"], "empresa": empresa}
