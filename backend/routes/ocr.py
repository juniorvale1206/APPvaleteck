import json
import re as _re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from core.config import EMERGENT_LLM_KEY
from core.rate_limit import limiter
from core.security import get_current_user
from models.ocr import PlateOcrIn, PlateOcrOut
from services.plates import extract_plate_from_text

router = APIRouter(prefix="/ocr", tags=["ocr"])


@router.post("/plate", response_model=PlateOcrOut)
@limiter.limit("15/minute")
async def ocr_plate(request: Request, payload: PlateOcrIn, user=Depends(get_current_user)):
    """Detecta placa brasileira em imagem usando Gemini Vision."""
    b64 = (payload.base64 or "").strip()
    if not b64:
        raise HTTPException(status_code=400, detail="Imagem obrigatória")
    if "," in b64:
        b64 = b64.split(",", 1)[1]
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    except ImportError:
        raise HTTPException(status_code=500, detail="emergentintegrations não instalado")
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY não configurado")

    session_id = f"ocr-plate-{user['id']}-{uuid.uuid4().hex[:6]}"
    system = (
        "You are an OCR expert specializing in Brazilian vehicle license plates. "
        "Detect the license plate in the image. Brazilian plates follow these formats:\n"
        "- Old: ABC1234 (3 letters + 4 digits)\n"
        "- Mercosul: ABC1D23 (3 letters + 1 digit + 1 letter + 2 digits)\n"
        "Respond ONLY with valid JSON: {\"plate\": \"ABC1D23\" or null, \"confidence\": 0.0-1.0, \"notes\": \"short reason\"}.\n"
        "If you see NO plate or cannot read it clearly, set plate=null and confidence<=0.3."
    )
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=session_id, system_message=system)
    chat.with_model("gemini", "gemini-2.5-flash")
    image = ImageContent(image_base64=b64)
    msg = UserMessage(
        text="Analise a imagem e responda apenas com o JSON com a placa detectada.",
        file_contents=[image],
    )
    try:
        raw = await chat.send_message(msg)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini Vision falhou: {e}")

    text = str(raw) if raw else ""
    plate: Optional[str] = None
    confidence = 0.0
    try:
        m = _re.search(r"\{[\s\S]*\}", text)
        if m:
            data = json.loads(m.group(0))
            p = (data.get("plate") or "").upper().replace("-", "").replace(" ", "")
            if p and _re.match(r"^[A-Z]{3}\d[A-Z0-9]\d{2}$", p):
                plate = p
                try:
                    confidence = float(data.get("confidence", 0.0))
                except Exception:
                    confidence = 0.5
    except Exception:
        pass
    if not plate:
        found = extract_plate_from_text(text)
        if found:
            plate = found
            confidence = 0.6
    return PlateOcrOut(plate=plate, confidence=round(confidence, 2), raw=text[:500], detected=plate is not None)
