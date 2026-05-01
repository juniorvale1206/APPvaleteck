import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from constants import COMPANIES
from core.config import DELAY_PENALTY_AMOUNT, DELAY_PENALTY_THRESHOLD_MIN
from core.database import db
from core.security import get_current_user
from models.appointment import AcceptIn, AppointmentOut, RefuseIn

router = APIRouter(prefix="/appointments", tags=["appointments"])


def _compute_delay(doc: dict) -> dict:
    sched = doc.get("scheduled_at")
    status = doc.get("status", "agendado")
    delay = 0
    penalty = 0.0
    if sched and status in ("agendado", "aceita"):
        try:
            s = datetime.fromisoformat(sched.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            diff = (now - s).total_seconds() / 60
            if diff > 0:
                delay = int(diff)
                if delay > DELAY_PENALTY_THRESHOLD_MIN:
                    penalty = DELAY_PENALTY_AMOUNT
        except Exception:
            pass
    doc["delay_min"] = delay
    doc["penalty_amount"] = penalty
    return doc


@router.get("", response_model=List[AppointmentOut])
async def list_appointments(user=Depends(get_current_user)):
    cursor = db.appointments.find({"user_id": user["id"]}, {"_id": 0}).sort("scheduled_at", 1)
    docs = await cursor.to_list(length=200)
    return [_compute_delay(d) for d in docs]


@router.get("/{aid}", response_model=AppointmentOut)
async def get_appointment(aid: str, user=Depends(get_current_user)):
    doc = await db.appointments.find_one({"id": aid, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return _compute_delay(doc)


@router.post("/{aid}/accept", response_model=AppointmentOut)
async def accept_appointment(aid: str, payload: AcceptIn, user=Depends(get_current_user)):
    doc = await db.appointments.find_one({"id": aid, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    if doc["status"] not in ("agendado",):
        raise HTTPException(status_code=400, detail="Apenas OS agendadas podem ser aceitas")
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.appointments.update_one(
        {"id": aid},
        {"$set": {"status": "aceita", "accepted_at": now_iso}},
    )
    updated = await db.appointments.find_one({"id": aid}, {"_id": 0})
    return _compute_delay(updated)


@router.post("/{aid}/refuse", response_model=AppointmentOut)
async def refuse_appointment(aid: str, payload: RefuseIn, user=Depends(get_current_user)):
    doc = await db.appointments.find_one({"id": aid, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    if doc["status"] not in ("agendado", "aceita"):
        raise HTTPException(status_code=400, detail="OS não pode ser recusada neste estado")
    if not payload.reason.strip():
        raise HTTPException(status_code=400, detail="Motivo da recusa é obrigatório")
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.appointments.update_one(
        {"id": aid},
        {"$set": {"status": "recusada", "refused_at": now_iso, "refuse_reason": payload.reason.strip()}},
    )
    updated = await db.appointments.find_one({"id": aid}, {"_id": 0})
    return _compute_delay(updated)


@router.post("/seed-new", response_model=AppointmentOut)
async def seed_new_appointment(user=Depends(get_current_user)):
    """Demo: gera uma nova OS aleatória agendada para hoje/amanhã."""
    nomes = [
        ("Pedro", "Almeida"), ("Lucas", "Pereira"), ("Ana", "Costa"), ("Beatriz", "Martins"),
        ("Felipe", "Rodrigues"), ("Juliana", "Ferreira"), ("Rafael", "Santos"), ("Camila", "Oliveira"),
    ]
    enderecos = [
        "Av. Brigadeiro Faria Lima, 3000 - São Paulo/SP",
        "R. Augusta, 1500 - São Paulo/SP",
        "Av. Atlântica, 800 - Rio de Janeiro/RJ",
        "Rua XV de Novembro, 200 - Curitiba/PR",
        "Av. Beira Mar, 450 - Florianópolis/SC",
    ]
    placas = ["XPT1A23", "QWE4B56", "ASD7C89", "ZXC1D45", "JKL3F67"]
    empresas_random = random.choice(COMPANIES)
    nome_sob = random.choice(nomes)
    horas_offset = random.choice([1, 3, 6, 24, 28])
    prioridade = random.choices(["alta", "normal", "baixa"], weights=[2, 5, 3])[0]
    eta = random.choice([45, 60, 90, 120])
    tipo_v = random.choice(["carro", "moto"])
    now = datetime.now(timezone.utc)
    aid = str(uuid.uuid4())
    nro_seq = await db.appointments.count_documents({}) + 1
    doc = {
        "id": aid,
        "user_id": user["id"],
        "numero_os": f"OS-2026-{nro_seq:04d}",
        "cliente_nome": nome_sob[0],
        "cliente_sobrenome": nome_sob[1],
        "placa": random.choice(placas),
        "empresa": empresas_random,
        "endereco": random.choice(enderecos),
        "scheduled_at": (now + timedelta(hours=horas_offset)).isoformat(),
        "status": "agendado",
        "checklist_id": None,
        "vehicle_type": tipo_v,
        "prioridade": prioridade,
        "telefone": f"(11) 9{random.randint(1000,9999)}-{random.randint(1000,9999)}",
        "tempo_estimado_min": eta,
        "created_at": now.isoformat(),
    }
    await db.appointments.insert_one(doc)
    doc.pop("_id", None)
    return doc
