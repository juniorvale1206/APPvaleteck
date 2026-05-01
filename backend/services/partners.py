"""Adapters de integração com sistemas dos parceiros (Rastremix, Telensat, etc).

No MVP, apenas Rastremix possui adapter mock determinístico. Implementações
reais só entram quando documentação/credenciais do parceiro estiverem disponíveis.
"""
import hashlib
import random
from datetime import datetime, timezone
from typing import List, Optional


class PartnerAdapter:
    name: str = "base"

    async def test_device(self, imei: str) -> Optional[dict]:
        return None

    async def sync_appointments(self, user_external_id: str) -> List[dict]:
        return []


class MockRastremixAdapter(PartnerAdapter):
    name = "rastremix"

    async def test_device(self, imei: str) -> Optional[dict]:
        if not (imei.isdigit() and len(imei) == 15):
            return None
        seed = int(hashlib.md5((imei + "rastremix").encode()).hexdigest(), 16)
        random.seed(seed)
        online = random.random() < 0.95
        latency = random.randint(60, 240) if online else 0
        return {
            "online": online,
            "latency_ms": latency,
            "message": (
                f"Dispositivo respondendo via Rastremix — último sinal agora, latência {latency}ms"
                if online else "Dispositivo offline — verifique alimentação e sinal GSM"
            ),
            "tested_at": datetime.now(timezone.utc).isoformat(),
        }


PARTNER_ADAPTERS: dict = {
    "rastremix": MockRastremixAdapter(),
}


def get_partner_adapter(empresa: str) -> Optional[PartnerAdapter]:
    return PARTNER_ADAPTERS.get(empresa.lower()) if empresa else None
