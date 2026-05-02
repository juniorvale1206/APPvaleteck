"""Validação de fotos via Gemini Vision (v14 Fase 3C - Check-in/Check-out do painel).

Verifica se uma foto é de:
- Painel de veículo
- Com ignição ligada (luzes do painel acesas)
- KM visível

Usado em /send-initial (entrada) e /finalize (saída) para garantir integridade do SLA.
"""
import json
import re
import uuid
from typing import Optional

from core.config import EMERGENT_LLM_KEY


async def validate_dashboard_photo(b64: str, user_id: str = "unknown") -> dict:
    """Valida se a foto é de um painel de veículo com ignição ligada.

    Retorna: {
        is_dashboard: bool,     # se é realmente um painel
        ignition_on: bool,       # se a ignição está ligada (luzes acesas)
        confidence: float 0-1,   # confiança total
        reason: str,             # motivo em português
        valid: bool,             # is_dashboard AND ignition_on AND confidence > 0.5
        raw: str,
    }
    """
    b64 = (b64 or "").strip()
    if not b64:
        return {"valid": False, "reason": "Imagem vazia", "confidence": 0.0,
                "is_dashboard": False, "ignition_on": False, "raw": ""}
    if "," in b64:
        b64 = b64.split(",", 1)[1]

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    except ImportError:
        # Degradação: se integração falhar, aceita mas com flag
        return {"valid": True, "reason": "Vision indisponível (auto-aprovado)", "confidence": 0.0,
                "is_dashboard": True, "ignition_on": True, "raw": "no-integration"}
    if not EMERGENT_LLM_KEY:
        return {"valid": True, "reason": "LLM_KEY ausente (auto-aprovado)", "confidence": 0.0,
                "is_dashboard": True, "ignition_on": True, "raw": "no-key"}

    session_id = f"dashboard-{user_id}-{uuid.uuid4().hex[:6]}"
    system = (
        "Você é um verificador antifraude de fotos de painel de veículos. Analise a imagem fornecida. "
        "Responda APENAS com JSON válido: "
        '{"is_dashboard": bool, "ignition_on": bool, "km_visible": bool, '
        '"confidence": float 0-1, "reason": "motivo em português (1 frase)"}. '
        "Regras:\n"
        "- is_dashboard=true SOMENTE se for painel de instrumentos de veículo (velocímetro, tacômetro, luzes).\n"
        "- ignition_on=true SOMENTE se houver luzes do painel acesas, ponteiros iluminados ou display digital ativo.\n"
        "- km_visible=true se o odômetro (KM) estiver visível.\n"
        "- confidence: sua certeza total (0.0=dúvida, 1.0=certeza).\n"
        "- reason: frase curta explicando (ex.: 'Painel com ignição ligada e KM visível')."
    )
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=session_id, system_message=system)
    chat.with_model("gemini", "gemini-2.5-flash")
    image = ImageContent(image_base64=b64)
    msg = UserMessage(
        text="Analise a foto e responda APENAS com o JSON.",
        file_contents=[image],
    )
    try:
        raw = await chat.send_message(msg)
    except Exception as e:
        return {"valid": False, "reason": f"Vision falhou: {e}", "confidence": 0.0,
                "is_dashboard": False, "ignition_on": False, "raw": str(e)[:300]}

    text = str(raw) if raw else ""
    try:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise ValueError("sem JSON")
        data = json.loads(m.group(0))
        is_dashboard = bool(data.get("is_dashboard"))
        ignition_on = bool(data.get("ignition_on"))
        km_visible = bool(data.get("km_visible", False))
        confidence = float(data.get("confidence") or 0.0)
        reason = str(data.get("reason") or "").strip()[:200]
    except Exception:
        return {
            "valid": False, "reason": f"Resposta inválida do Vision: {text[:120]}",
            "confidence": 0.0, "is_dashboard": False, "ignition_on": False,
            "raw": text[:500],
        }

    valid = is_dashboard and ignition_on and confidence >= 0.5
    return {
        "valid": valid,
        "is_dashboard": is_dashboard,
        "ignition_on": ignition_on,
        "km_visible": km_visible,
        "confidence": round(confidence, 2),
        "reason": reason or ("OK" if valid else "Requisitos não atendidos"),
        "raw": text[:500],
    }
