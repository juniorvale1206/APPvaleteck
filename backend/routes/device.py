import hashlib
import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from core.database import db
from core.security import get_current_user
from models.device import DeviceTestIn, DeviceTestOut
from services.partners import get_partner_adapter

router = APIRouter(prefix="/device", tags=["device"])


@router.post("/test", response_model=DeviceTestOut)
async def test_device(payload: DeviceTestIn, user=Depends(get_current_user)):
    """Teste de comunicação do rastreador pelo IMEI."""
    imei = (payload.imei or "").strip()
    if not imei or not imei.isdigit() or len(imei) != 15:
        raise HTTPException(status_code=400, detail="IMEI inválido (15 dígitos)")
    last = await db.checklists.find_one(
        {"imei": imei},
        {"_id": 0, "empresa": 1},
        sort=[("created_at", -1)],
    )
    adapter = get_partner_adapter((last or {}).get("empresa", "")) if last else None
    if adapter is not None:
        result = await adapter.test_device(imei)
        if result is not None:
            return DeviceTestOut(**result, source=f"partner:{adapter.name}")
    seed = int(hashlib.md5(imei.encode()).hexdigest(), 16)
    random.seed(seed)
    online = random.random() < 0.9
    latency = random.randint(80, 380) if online else 0
    now_iso = datetime.now(timezone.utc).isoformat()
    msg = (
        f"Dispositivo respondendo — último sinal agora, latência {latency}ms"
        if online else "Dispositivo offline — verifique alimentação, antena e conexão GSM"
    )
    return DeviceTestOut(online=online, latency_ms=latency, message=msg, tested_at=now_iso, source="mock")
