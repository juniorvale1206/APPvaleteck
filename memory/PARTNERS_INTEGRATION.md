# Valeteck — Guia de integração para parceiros (Rastremix, Telensat, GPS My, GPS Joy, Topy Pro)

## 1. Webhook IN — Criar OS no Valeteck a partir do sistema do parceiro

### Endpoint
```
POST {EMERGENT_BACKEND_URL}/api/partners/webhook/appointments
Content-Type: application/json
```

### Payload
```json
{
  "partner": "rastremix | telensat | gps_my | gps_joy | topy_pro | valeteck",
  "user_email": "tecnico@valeteck.com",
  "numero_os": "RTX-2026-98765",
  "cliente_nome": "João",
  "cliente_sobrenome": "Silva",
  "placa": "ABC1D23",
  "endereco": "Av. Paulista, 1000 - São Paulo/SP",
  "scheduled_at": "2026-05-03T14:30:00Z",
  "telefone": "(11) 99999-1111",
  "vehicle_type": "carro",
  "vehicle_brand": "Fiat",
  "vehicle_model": "Strada",
  "vehicle_year": "2024",
  "prioridade": "alta",
  "tempo_estimado_min": 90,
  "observacoes": "Portaria: pedir por Carlos",
  "comissao": 120.00,
  "secret": "<PARTNER_WEBHOOK_SECRET>"
}
```

### Autenticação
Shared secret no body (`secret`). Configurado em `PARTNER_WEBHOOK_SECRET` (env). Em produção, migrar para HMAC + timestamp + rotação.

### Resposta
```json
{ "ok": true, "appointment_id": "<uuid>", "empresa": "Rastremix" }
```

---

## 2. Adapter OUT — Integração para teste de dispositivo (e futuro: sincronizar status de OS)

### Arquitetura
- Classe base `PartnerAdapter` em `/app/backend/server.py`
- Registro em `PARTNER_ADAPTERS = { "rastremix": MockRastremixAdapter(), ... }`
- `get_partner_adapter(empresa)` descobre o adapter pelo nome da empresa (case-insensitive)
- Usado em `POST /api/device/test` → se último checklist com o IMEI tiver empresa conhecida, usa adapter; senão fallback mock

### Para trocar Mock pela implementação real (exemplo Rastremix)

```python
import httpx

class RastremixAdapter(PartnerAdapter):
    name = "rastremix"

    async def test_device(self, imei: str) -> Optional[dict]:
        base = os.environ["RASTREMIX_BASE_URL"]   # ex: https://api.rastremix.com
        token = os.environ["RASTREMIX_API_TOKEN"]
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(
                f"{base}/v1/devices/{imei}/status",
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code != 200:
                return None
            data = r.json()
            return {
                "online": bool(data.get("online")),
                "latency_ms": int(data.get("last_ping_ms", 0)),
                "message": data.get("status_text", ""),
                "tested_at": data.get("checked_at") or datetime.now(timezone.utc).isoformat(),
            }

    async def sync_appointments(self, user_external_id: str) -> List[dict]:
        # TODO: poll OS abertas no sistema do parceiro e mapear para formato AppointmentOut
        ...


PARTNER_ADAPTERS["rastremix"] = RastremixAdapter()
```

### Variáveis de ambiente esperadas (a serem fornecidas pelo parceiro)
```
RASTREMIX_BASE_URL=https://api.rastremix.com
RASTREMIX_API_TOKEN=<token fornecido pela Rastremix>

TELENSAT_BASE_URL=...
TELENSAT_API_KEY=...

# Repetir para cada parceiro
```

---

## 3. Próximos passos para produção
1. Coletar credenciais + URL base + docs de cada parceiro (Rastremix, Telensat, GPS My, GPS Joy, Topy Pro)
2. Implementar um adapter real por parceiro seguindo o exemplo
3. Rodar `pytest tests/test_valeteck_v9.py` para não quebrar regressão
4. Trocar shared-secret do webhook por HMAC rotativo
5. Adicionar rate-limiting e IP allow-list no webhook em produção
