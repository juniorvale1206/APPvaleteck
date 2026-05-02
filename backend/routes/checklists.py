import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from constants import COMPANIES
from core.database import db
from core.security import get_current_user
from core.config import CLOUDINARY_ENABLED, CLOUDINARY_FOLDER
from core.storage import upload_base64_image
from services.alerts import build_alerts
from services.inventory import categorize_equipment, default_equipment_value, compute_reverse_deadline
from services.pdf import render_checklist_pdf
from services.plates import normalize_plate, valid_plate
from models.checklist import ChecklistInput, ChecklistOut, PhotoIn, RemovedEquipmentIn
from models.service_types import SERVICE_TYPES

router = APIRouter(prefix="/checklists", tags=["checklists"])


def _svc_name(code: Optional[str]) -> str:
    st = SERVICE_TYPES.get(code or "")
    return st.name if st else ""


def _svc_max_minutes(code: Optional[str]) -> int:
    st = SERVICE_TYPES.get(code or "")
    return st.max_minutes if st else 0


def _svc_base_value(code: Optional[str]) -> float:
    st = SERVICE_TYPES.get(code or "")
    return st.base_value if st else 0.0


def _svc_within(code: Optional[str], elapsed_sec: int) -> Optional[bool]:
    st = SERVICE_TYPES.get(code or "")
    if not st or not elapsed_sec:
        return None
    return (elapsed_sec / 60.0) <= st.max_minutes


async def _apply_inventory_ops(payload: ChecklistInput, user_id: str, checklist_id: str, numero: str) -> List[dict]:
    """Sincroniza O.S ↔ Estoque quando o checklist é ENVIADO.

    Regras:
    - Para cada `removed_equipments`: cria item no estoque com status=pending_reverse
      (deadline calculado) — vinculado ao checklist_id.
    - Se `installed_from_inventory_id`: move o item do estoque do técnico para
      status=installed, grava placa + checklist_id.
    - Match por IMEI: se não veio installed_from_inventory_id mas há item do técnico
      com status=with_tech e IMEI igual ao do checklist, faz o match automático.
    """
    ops: List[dict] = []
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # 1) Equipamentos RETIRADOS → criar em pending_reverse
    for eq in payload.removed_equipments or []:
        cat = categorize_equipment(eq.tipo, eq.modelo or "")
        item_id = str(uuid.uuid4())
        doc = {
            "id": item_id,
            "user_id": user_id,
            "tipo": eq.tipo or "Rastreador",
            "modelo": eq.modelo or "",
            "imei": (eq.imei or "").strip(),
            "iccid": (eq.iccid or "").strip(),
            "serie": (eq.serie or "").strip(),
            "empresa": eq.empresa or payload.empresa,
            "status": "pending_reverse",
            "checklist_id": checklist_id,
            "placa": normalize_plate(payload.placa),
            "tracking_code": "",
            "equipment_category": cat,
            "equipment_value": default_equipment_value(cat),
            "pending_reverse_at": now_iso,
            "reverse_deadline_at": compute_reverse_deadline(now).isoformat(),
            "reverse_notes": eq.notes or f"Retirado da O.S {numero} (estado: {eq.estado or 'funcional'})",
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        await db.inventory.insert_one(doc)
        ops.append({
            "op": "removed_added_to_reverse",
            "inventory_id": item_id,
            "modelo": doc["modelo"], "imei": doc["imei"], "serie": doc["serie"],
            "category": cat, "value": doc["equipment_value"],
        })

    # 2) Equipamento INSTALADO (match)
    target_id = payload.installed_from_inventory_id
    if not target_id:
        imei = (payload.imei or "").strip()
        if imei:
            found = await db.inventory.find_one(
                {"user_id": user_id, "imei": imei, "status": {"$in": ["with_tech", "in_transit_to_tech"]}},
                {"_id": 0, "id": 1},
            )
            if found:
                target_id = found["id"]
    if target_id:
        result = await db.inventory.update_one(
            {"id": target_id, "user_id": user_id},
            {"$set": {
                "status": "installed",
                "placa": normalize_plate(payload.placa),
                "checklist_id": checklist_id,
                "updated_at": now_iso,
            }},
        )
        if result.modified_count:
            ops.append({"op": "installed_from_inventory", "inventory_id": target_id})

    return ops


def _validate_send(c: dict) -> List[str]:
    errors: List[str] = []
    if not c.get("nome", "").strip():
        errors.append("Nome obrigatório")
    if not c.get("sobrenome", "").strip():
        errors.append("Sobrenome obrigatório")
    if not c.get("placa", "").strip():
        errors.append("Placa obrigatória")
    elif not valid_plate(c["placa"]):
        errors.append("Placa inválida")
    if not c.get("empresa", "").strip():
        errors.append("Empresa obrigatória")
    elif c["empresa"] not in COMPANIES:
        errors.append("Empresa inválida")
    if not c.get("equipamento", "").strip():
        errors.append("Equipamento obrigatório")
    photos = c.get("photos", [])
    if len(photos) < 2:
        errors.append("Mínimo de 2 fotos obrigatórias")
    steps_present = {p.get("workflow_step") for p in photos if p.get("workflow_step")}
    if steps_present and not {1, 2, 3, 4}.issubset(steps_present):
        faltantes = sorted({1, 2, 3, 4} - steps_present)
        errors.append(f"Fotos faltantes nos grupos: {', '.join(str(s) for s in faltantes)}")
    if not c.get("signature_base64", "").strip() and not c.get("signature_url", ""):
        errors.append("Assinatura obrigatória")
    imei = (c.get("imei") or "").strip()
    if imei and not (imei.isdigit() and len(imei) == 15):
        errors.append("IMEI deve ter 15 dígitos")
    return errors


def _to_out(doc: dict) -> ChecklistOut:
    return ChecklistOut(**{k: v for k, v in doc.items() if k != "_id" and k != "plate_norm"})


def _process_photos_for_storage(photos: List[PhotoIn], cid: str, user_id: str) -> List[dict]:
    """Para cada foto, se Cloudinary estiver ON e veio base64, faz upload e
    substitui base64 por url. Mantém base64 caso o upload falhe."""
    out: List[dict] = []
    for idx, p in enumerate(photos):
        d = p.dict() if isinstance(p, PhotoIn) else dict(p)
        if CLOUDINARY_ENABLED and not d.get("url") and d.get("base64"):
            url = upload_base64_image(
                d["base64"],
                folder=f"{CLOUDINARY_FOLDER}/checklists/{cid}",
                public_id=f"photo-{idx:03d}-{(d.get('photo_id') or uuid.uuid4().hex[:6])}",
            )
            if url:
                d["url"] = url
                d["base64"] = ""  # libera espaço no Mongo
        out.append(d)
    return out


def _process_signature_for_storage(b64: str, cid: str) -> tuple[str, Optional[str]]:
    """Sobe a assinatura para Cloudinary se ativo. Retorna (base64_residual, url)."""
    if not b64 or not CLOUDINARY_ENABLED:
        return b64 or "", None
    url = upload_base64_image(
        b64,
        folder=f"{CLOUDINARY_FOLDER}/checklists/{cid}",
        public_id="signature",
    )
    if url:
        return "", url
    return b64, None


@router.get("", response_model=List[ChecklistOut])
async def list_checklists(q: Optional[str] = None, user=Depends(get_current_user)):
    query: dict = {"user_id": user["id"]}
    if q:
        s = q.strip()
        regex = {"$regex": re.escape(s), "$options": "i"}
        query["$or"] = [
            {"placa": regex},
            {"nome": regex},
            {"sobrenome": regex},
            {"plate_norm": {"$regex": re.escape(normalize_plate(s)), "$options": "i"}},
        ]
    cursor = db.checklists.find(query, {"_id": 0}).sort("created_at", -1)
    docs = await cursor.to_list(length=500)
    return [_to_out(d) for d in docs]


@router.post("", response_model=ChecklistOut)
async def create_checklist(payload: ChecklistInput, user=Depends(get_current_user)):
    status = payload.status if payload.status in ("rascunho", "enviado") else "rascunho"
    if status == "enviado":
        errors = _validate_send(payload.dict())
        if errors:
            raise HTTPException(status_code=400, detail="; ".join(errors))

    now_iso = datetime.now(timezone.utc).isoformat()
    cid = str(uuid.uuid4())
    numero = "VT-" + datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + cid[:6].upper()

    alerts: List[str] = []
    if status == "enviado":
        alerts = await build_alerts(payload, user["id"])

    photos = _process_photos_for_storage(payload.photos, cid, user["id"])
    sig_b64_residual, sig_url = _process_signature_for_storage(payload.signature_base64 or "", cid)

    doc = {
        "id": cid,
        "numero": numero,
        "user_id": user["id"],
        "status": status,
        "vehicle_type": payload.vehicle_type or "",
        "vehicle_brand": payload.vehicle_brand or "",
        "vehicle_model": payload.vehicle_model or "",
        "vehicle_year": payload.vehicle_year or "",
        "vehicle_color": payload.vehicle_color or "",
        "vehicle_vin": payload.vehicle_vin or "",
        "vehicle_odometer": payload.vehicle_odometer,
        "problems_client": payload.problems_client or [],
        "problems_client_other": payload.problems_client_other or "",
        "problems_technician": payload.problems_technician or [],
        "problems_technician_other": payload.problems_technician_other or "",
        "battery_state": payload.battery_state or "",
        "battery_voltage": payload.battery_voltage,
        "imei": (payload.imei or "").strip(),
        "iccid": (payload.iccid or "").strip(),
        "device_online": payload.device_online,
        "device_tested_at": payload.device_tested_at or "",
        "device_test_message": payload.device_test_message or "",
        "execution_started_at": payload.execution_started_at or "",
        "execution_ended_at": payload.execution_ended_at or "",
        "execution_elapsed_sec": payload.execution_elapsed_sec or 0,
        # v14 — Motor de Comissionamento: snapshot do SLA no momento do envio
        "service_type_code": payload.service_type_code or "",
        "service_type_name": _svc_name(payload.service_type_code),
        "sla_max_minutes": _svc_max_minutes(payload.service_type_code),
        "sla_base_value": _svc_base_value(payload.service_type_code),
        "sla_within": _svc_within(payload.service_type_code, payload.execution_elapsed_sec or 0),
        "appointment_id": payload.appointment_id or "",
        "nome": payload.nome.strip(),
        "sobrenome": payload.sobrenome.strip(),
        "placa": normalize_plate(payload.placa),
        "plate_norm": normalize_plate(payload.placa),
        "telefone": payload.telefone or "",
        "obs_iniciais": payload.obs_iniciais or "",
        "empresa": payload.empresa,
        "equipamento": payload.equipamento,
        "tipo_atendimento": payload.tipo_atendimento or "",
        "acessorios": payload.acessorios or [],
        "obs_tecnicas": payload.obs_tecnicas or "",
        "photos": photos,
        "location": payload.location,
        "location_available": payload.location_available,
        "signature_base64": sig_b64_residual,
        "signature_url": sig_url,
        "alerts": alerts,
        "removed_equipments": [r.dict() for r in (payload.removed_equipments or [])],
        "installed_from_inventory_id": payload.installed_from_inventory_id,
        "inventory_ops": [],
        "created_at": now_iso,
        "updated_at": now_iso,
        "sent_at": now_iso if status == "enviado" else None,
    }
    # Sincroniza estoque ANTES de inserir para gravar o log
    if status == "enviado":
        doc["inventory_ops"] = await _apply_inventory_ops(payload, user["id"], cid, numero)
    await db.checklists.insert_one(doc)
    doc.pop("_id", None)
    if payload.appointment_id:
        await db.appointments.update_one(
            {"id": payload.appointment_id, "user_id": user["id"]},
            {"$set": {"checklist_id": cid, "status": "concluido" if status == "enviado" else "em_andamento"}},
        )
    return _to_out(doc)


# =========================================================================
# v14.1 — Anti-fraude SLA: endpoints server-side para iniciar/finalizar SLA
# =========================================================================
INSTALL_CATEGORIES = {"instalacao", "telemetria"}
EQUIPMENT_PHOTO_WINDOW_SEC = 180  # 3 minutos


def _sla_requires_equipment_photo(service_type_code: str) -> bool:
    st = SERVICE_TYPES.get(service_type_code or "")
    return bool(st and st.category in INSTALL_CATEGORIES)


class SendInitialPayload(BaseModel):
    service_type_code: str
    dashboard_photo_base64: str        # v14 Fase 3C — foto obrigatória do painel (check-in)
    # Dados mínimos iniciais (podem já estar salvos no rascunho)
    nome: Optional[str] = None
    sobrenome: Optional[str] = None
    placa: Optional[str] = None
    cpf: Optional[str] = None
    empresa: Optional[str] = None
    tipo_atendimento: Optional[str] = None


class EquipmentPhotoPayload(BaseModel):
    photo_base64: str


class FinalizePayload(BaseModel):
    dashboard_photo_base64: str        # v14 Fase 3C — foto obrigatória do painel (check-out)


@router.post("/{cid}/send-initial", response_model=ChecklistOut)
async def send_initial_checklist(cid: str, payload: SendInitialPayload, user=Depends(get_current_user)):
    """Inicia oficialmente o SLA server-side. Exige foto do painel (check-in) com
    validação via Gemini Vision (antifraude).

    - Valida `service_type_code` no catálogo.
    - Valida que foto é um painel com ignição ligada.
    - Se inválida, retorna 422 com motivo.
    """
    st = SERVICE_TYPES.get(payload.service_type_code)
    if not st:
        raise HTTPException(status_code=400, detail="service_type_code inválido")
    if st.level_restriction and user.get("level") != st.level_restriction:
        raise HTTPException(status_code=403, detail=f"Serviço restrito a nível {st.level_restriction.upper()}")
    if not (payload.dashboard_photo_base64 or "").strip():
        raise HTTPException(status_code=400, detail="dashboard_photo_base64 obrigatório (check-in do painel)")

    doc = await db.checklists.find_one({"id": cid, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")
    if doc.get("phase") not in (None, "", "draft"):
        raise HTTPException(status_code=409, detail=f"Checklist já iniciado (phase={doc.get('phase')})")

    # Validação visual (Gemini Vision) — antifraude
    from services.vision import validate_dashboard_photo
    v = await validate_dashboard_photo(payload.dashboard_photo_base64, user_id=user["id"])
    if not v.get("valid"):
        raise HTTPException(
            status_code=422,
            detail=f"Foto do painel inválida: {v.get('reason', 'não é um painel com ignição ligada')}",
        )

    now = datetime.now(timezone.utc).isoformat()
    photo_url = payload.dashboard_photo_base64
    if CLOUDINARY_ENABLED:
        try:
            photo_url = upload_base64_image(
                payload.dashboard_photo_base64, folder=CLOUDINARY_FOLDER,
                public_id=f"{cid}_dashboard_in",
            )
        except Exception:
            pass

    update: dict = {
        "service_type_code": st.code.value,
        "service_type_name": st.name,
        "sla_max_minutes": st.max_minutes,
        "sla_base_value": st.base_value,
        "checklist_sent_at": now,
        "phase": "awaiting_equipment_photo" if _sla_requires_equipment_photo(st.code.value) else "in_execution",
        "dashboard_photo_in_url": photo_url,
        "dashboard_photo_in_at": now,
        "dashboard_photo_in_valid": v.get("valid", False),
        "dashboard_photo_in_reason": v.get("reason", ""),
        "dashboard_photo_in_confidence": v.get("confidence", 0.0),
        "updated_at": now,
    }
    for key in ("nome", "sobrenome", "placa", "cpf", "empresa", "tipo_atendimento"):
        val = getattr(payload, key, None)
        if val:
            if key == "placa":
                update["placa"] = normalize_plate(val)
                update["plate_norm"] = normalize_plate(val)
            else:
                update[key] = val

    await db.checklists.update_one({"id": cid}, {"$set": update})
    updated = await db.checklists.find_one({"id": cid}, {"_id": 0})
    return _to_out(updated)


@router.post("/{cid}/equipment-photo", response_model=ChecklistOut)
async def upload_equipment_photo(cid: str, payload: EquipmentPhotoPayload, user=Depends(get_current_user)):
    """Registra a foto unificada do equipamento (rastreador+IMEI+placa/chassi).

    - Calcula delay em segundos desde `checklist_sent_at`.
    - Se delay > 180s, marca `equipment_photo_flag=true` (alerta para admin).
    - Nunca bloqueia o fluxo (conforme regra D = apenas alerta).
    """
    doc = await db.checklists.find_one({"id": cid, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")
    sent_at = doc.get("checklist_sent_at")
    if not sent_at:
        raise HTTPException(status_code=409, detail="Checklist inicial não foi enviado ainda")

    try:
        sent_dt = datetime.fromisoformat(sent_at.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(status_code=500, detail="checklist_sent_at inválido")
    now = datetime.now(timezone.utc)
    delay_sec = int((now - sent_dt).total_seconds())
    flag = delay_sec > EQUIPMENT_PHOTO_WINDOW_SEC

    # Salva foto (base64 direto por enquanto; Cloudinary futuro)
    photo_url = ""
    if CLOUDINARY_ENABLED:
        photo_url = upload_base64_image(payload.photo_base64, folder=CLOUDINARY_FOLDER, public_id=f"{cid}_equipment")
    else:
        photo_url = payload.photo_base64  # base64 direto

    update = {
        "equipment_photo_url": photo_url,
        "equipment_photo_at": now.isoformat(),
        "equipment_photo_delay_sec": delay_sec,
        "equipment_photo_flag": flag,
        "phase": "in_execution",
        "updated_at": now.isoformat(),
    }
    await db.checklists.update_one({"id": cid}, {"$set": update})
    updated = await db.checklists.find_one({"id": cid}, {"_id": 0})
    return _to_out(updated)


@router.post("/{cid}/finalize", response_model=ChecklistOut)
async def finalize_service(cid: str, payload: FinalizePayload, user=Depends(get_current_user)):
    """Encerra o SLA server-side. Exige foto do painel (check-out) com validação Vision.

    Calcula sla_total_sec e marca phase=finalized.
    """
    if not (payload.dashboard_photo_base64 or "").strip():
        raise HTTPException(status_code=400, detail="dashboard_photo_base64 obrigatório (check-out do painel)")

    doc = await db.checklists.find_one({"id": cid, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")
    sent_at = doc.get("checklist_sent_at")
    if not sent_at:
        raise HTTPException(status_code=409, detail="Cronômetro nunca foi iniciado")
    if doc.get("service_finished_at"):
        raise HTTPException(status_code=409, detail="Serviço já foi finalizado")

    # Validação visual (Gemini Vision)
    from services.vision import validate_dashboard_photo
    v = await validate_dashboard_photo(payload.dashboard_photo_base64, user_id=user["id"])
    if not v.get("valid"):
        raise HTTPException(
            status_code=422,
            detail=f"Foto do painel inválida: {v.get('reason', 'não é um painel com ignição ligada')}",
        )

    try:
        sent_dt = datetime.fromisoformat(sent_at.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(status_code=500, detail="checklist_sent_at inválido")
    now = datetime.now(timezone.utc)
    total_sec = int((now - sent_dt).total_seconds())
    within = None
    sla_max = doc.get("sla_max_minutes") or 0
    if sla_max > 0:
        within = (total_sec / 60.0) <= sla_max

    photo_url = payload.dashboard_photo_base64
    if CLOUDINARY_ENABLED:
        try:
            photo_url = upload_base64_image(
                payload.dashboard_photo_base64, folder=CLOUDINARY_FOLDER,
                public_id=f"{cid}_dashboard_out",
            )
        except Exception:
            pass

    await db.checklists.update_one({"id": cid}, {"$set": {
        "service_finished_at": now.isoformat(),
        "sla_total_sec": total_sec,
        "execution_elapsed_sec": total_sec,
        "execution_ended_at": now.isoformat(),
        "execution_started_at": sent_at,
        "sla_within": within,
        "phase": "finalized",
        "dashboard_photo_out_url": photo_url,
        "dashboard_photo_out_at": now.isoformat(),
        "dashboard_photo_out_valid": v.get("valid", False),
        "dashboard_photo_out_reason": v.get("reason", ""),
        "dashboard_photo_out_confidence": v.get("confidence", 0.0),
        "updated_at": now.isoformat(),
    }})
    updated = await db.checklists.find_one({"id": cid}, {"_id": 0})
    return _to_out(updated)




@router.get("/{cid}", response_model=ChecklistOut)
async def get_checklist(cid: str, user=Depends(get_current_user)):
    # Admin pode ver qualquer checklist (para auditoria)
    if user.get("role") == "admin":
        doc = await db.checklists.find_one({"id": cid}, {"_id": 0})
    else:
        doc = await db.checklists.find_one({"id": cid, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")
    return _to_out(doc)


@router.put("/{cid}", response_model=ChecklistOut)
async def update_checklist(cid: str, payload: ChecklistInput, user=Depends(get_current_user)):
    existing = await db.checklists.find_one({"id": cid, "user_id": user["id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")
    if existing["status"] not in ("rascunho",):
        raise HTTPException(status_code=400, detail="Apenas rascunhos podem ser editados")

    status = payload.status if payload.status in ("rascunho", "enviado") else "rascunho"
    if status == "enviado":
        errors = _validate_send(payload.dict())
        if errors:
            raise HTTPException(status_code=400, detail="; ".join(errors))

    alerts: List[str] = existing.get("alerts", [])
    if status == "enviado":
        alerts = await build_alerts(payload, user["id"], exclude_id=cid)

    photos = _process_photos_for_storage(payload.photos, cid, user["id"])
    sig_b64_residual, sig_url = _process_signature_for_storage(payload.signature_base64 or "", cid)

    now_iso = datetime.now(timezone.utc).isoformat()
    update = {
        "status": status,
        "vehicle_type": payload.vehicle_type or "",
        "vehicle_brand": payload.vehicle_brand or "",
        "vehicle_model": payload.vehicle_model or "",
        "vehicle_year": payload.vehicle_year or "",
        "vehicle_color": payload.vehicle_color or "",
        "vehicle_vin": payload.vehicle_vin or "",
        "vehicle_odometer": payload.vehicle_odometer,
        "problems_client": payload.problems_client or [],
        "problems_client_other": payload.problems_client_other or "",
        "problems_technician": payload.problems_technician or [],
        "problems_technician_other": payload.problems_technician_other or "",
        "battery_state": payload.battery_state or "",
        "battery_voltage": payload.battery_voltage,
        "imei": (payload.imei or "").strip(),
        "iccid": (payload.iccid or "").strip(),
        "device_online": payload.device_online,
        "device_tested_at": payload.device_tested_at or "",
        "device_test_message": payload.device_test_message or "",
        "execution_started_at": payload.execution_started_at or "",
        "execution_ended_at": payload.execution_ended_at or "",
        "execution_elapsed_sec": payload.execution_elapsed_sec or 0,
        "nome": payload.nome.strip(),
        "sobrenome": payload.sobrenome.strip(),
        "placa": normalize_plate(payload.placa),
        "plate_norm": normalize_plate(payload.placa),
        "telefone": payload.telefone or "",
        "obs_iniciais": payload.obs_iniciais or "",
        "empresa": payload.empresa,
        "equipamento": payload.equipamento,
        "tipo_atendimento": payload.tipo_atendimento or "",
        "acessorios": payload.acessorios or [],
        "obs_tecnicas": payload.obs_tecnicas or "",
        "photos": photos,
        "location": payload.location,
        "location_available": payload.location_available,
        "signature_base64": sig_b64_residual if sig_b64_residual or sig_url else (existing.get("signature_base64", "")),
        "signature_url": sig_url or existing.get("signature_url"),
        "alerts": alerts,
        "updated_at": now_iso,
    }
    if status == "enviado" and not existing.get("sent_at"):
        update["sent_at"] = now_iso

    await db.checklists.update_one({"id": cid}, {"$set": update})
    doc = await db.checklists.find_one({"id": cid}, {"_id": 0})
    return _to_out(doc)


@router.delete("/{cid}")
async def delete_checklist(cid: str, user=Depends(get_current_user)):
    existing = await db.checklists.find_one({"id": cid, "user_id": user["id"]})
    if not existing:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")
    if existing["status"] != "rascunho":
        raise HTTPException(status_code=400, detail="Apenas rascunhos podem ser excluídos")
    await db.checklists.delete_one({"id": cid})
    return {"ok": True}


@router.get("/{cid}/pdf")
async def checklist_pdf(cid: str, user=Depends(get_current_user)):
    # Admin pode baixar PDF de qualquer técnico (para auditoria)
    if user.get("role") == "admin":
        doc = await db.checklists.find_one({"id": cid}, {"_id": 0})
    else:
        doc = await db.checklists.find_one({"id": cid, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")
    pdf_bytes = render_checklist_pdf(doc)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=checklist-{doc['numero']}.pdf"},
    )
